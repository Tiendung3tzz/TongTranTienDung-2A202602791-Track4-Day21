"""Controlled, separate eps / RANSAC sweeps on three KITTI frames.

python -m src.experiment
Latency includes finite/ROI, voxel, ground fit/classification, DBSCAN and AABBs;
excludes imports, file IO, GT diagnostics and plotting. One warm-up per config.
"""
from __future__ import annotations
import argparse
import csv
import json
import platform
import sys
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter

from src.obstacle import Config, run_pipeline, save_demo
import numpy as np
import open3d as o3d
import pandas as pd
import matplotlib.pyplot as plt
from starter.datasets import load_frame, dataset_type
from src.evaluation import gt_support


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No results for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def hardware_info(repeats):
    import psutil
    cpu = platform.processor()
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return {"cpu": cpu, "ram_gib": round(psutil.virtual_memory().total / 2**30, 2),
            "gpu_used": False, "platform": platform.platform(), "python": platform.python_version(),
            "open3d": o3d.__version__, "numpy": np.__version__, "omp_threads": 1,
            "warmups_per_config": 1, "measured_repeats": repeats,
            "timed_stages": "finite/ROI, voxel, RANSAC, classification, DBSCAN, AABB; excludes IO/plots/GT"}


def plot_sweeps(rows, path):
    df = pd.DataFrame(rows)
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), constrained_layout=True)
    for i, (sweep, label) in enumerate((("eps", "DBSCAN eps (m)"), ("distance_threshold", "RANSAC threshold (m)"))):
        for frame, group in df[df.sweep == sweep].groupby("frame"):
            for ax, metric in zip(axes[i], ("n_clusters", "nearest_m", "latency_p50_ms")):
                ax.plot(group.level_m, group[metric], "o-", label=frame)
                ax.set(xlabel=label)
                ax.grid(alpha=.25)
        for ax, title in zip(axes[i], ("Number of clusters", "Nearest AABB distance (m)", "Pipeline latency p50 (ms)")):
            ax.set_title(title)
        for ax, metric in zip(axes[i], ("n_clusters", "nearest_m", "latency_p50_ms")):
            ax.set_ylim(0, float(df[df.sweep == sweep][metric].max()) * 1.1)
        axes[i, 0].legend(title="KITTI frame")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data/kitti_mini", help="KITTI root, x-forward/y-left/z-up")
    ap.add_argument("--frames", nargs="+", default=["000008", "000011", "000049"], help="At least three frame IDs")
    ap.add_argument("--eps-levels", nargs="+", type=float, default=[.3, .5, .8], help="Separate eps sweep (m)")
    ap.add_argument("--ground-levels", nargs="+", type=float, default=[.05, .1, .3], help="Separate RANSAC threshold sweep (m)")
    ap.add_argument("--repeats", type=int, default=20, help="Measured runs after one warm-up, minimum 20")
    ap.add_argument("--seed", type=int, default=42, help="Fixed RANSAC seed")
    ap.add_argument("--out-dir", default="results", help="CSV/JSON outputs; figures stored in figures/")
    args = ap.parse_args()
    if args.repeats < 20 or len(set(args.frames)) < 3:
        ap.error("Require >=20 repeats and >=3 distinct frames")
    if dataset_type(args.data_root) != "kitti":
        ap.error("This pipeline requires KITTI LiDAR axes")
    for levels in (args.eps_levels, args.ground_levels):
        if len(set(levels)) < 3:
            ap.error("Each sweep requires >=3 distinct levels")
    base = Config(seed=args.seed)
    out = Path(args.out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    rows, latency_rows, cluster_rows, gt_rows = [], [], [], []
    for frame in args.frames:
        fr = load_frame(args.data_root, frame)
        for sweep, levels in (("eps", args.eps_levels), ("distance_threshold", args.ground_levels)):
            for level in levels:
                cfg = replace(base, **{sweep: level})
                reference = run_pipeline(fr["points"], cfg)  # discarded warm-up
                times = []
                meta = {"dataset": Path(args.data_root).name, "frame": frame, "sweep": sweep, "level_m": level, **asdict(cfg)}
                for repeat in range(args.repeats):
                    start = perf_counter()
                    result = run_pipeline(fr["points"], cfg)
                    ms = (perf_counter() - start) * 1000
                    # Require stable numerical results, not identical wall-clock times.
                    np.testing.assert_allclose(result["plane"], reference["plane"], atol=1e-10)
                    np.testing.assert_array_equal(result["labels"], reference["labels"])
                    times.append(ms)
                    latency_rows.append({**meta, "repeat": repeat+1, "latency_ms": ms})
                row = {**meta, **result["metrics"], "latency_p50_ms": float(np.percentile(times, 50)),
                       "latency_p95_ms": float(np.percentile(times, 95)), "repeats": args.repeats,
                       **{f"plane_{key}": value for key, value in zip("abcd", result["plane"])}}
                rows.append(row)
                for box in result["boxes"]:
                    cluster_rows.append({**meta, "cluster_id": box["cluster_id"], "n_points": box["n_points"],
                                         **{f"min_{axis}_m": v for axis, v in zip("xyz", box["lo"])},
                                         **{f"max_{axis}_m": v for axis, v in zip("xyz", box["hi"])},
                                         **{f"size_{axis}_m": v for axis, v in zip("xyz", box["extent"])},
                                         "nearest_m": box["nearest_m"]})
                gt_rows.extend({**meta, **g} for g in gt_support(fr, result))
                print(f"{frame} {sweep}={level}: clusters={row['n_clusters']} nearest={row['nearest_m']:.3f}m p50={row['latency_p50_ms']:.2f}ms", flush=True)
                if sweep == "eps" and level == base.eps:
                    save_demo(result, cfg, frame, out / "figures" / f"obstacle_demo_{frame}.png")
    write_csv(out / "obstacle_sweep.csv", rows)
    write_csv(out / "obstacle_latency.csv", latency_rows)
    write_csv(out / "obstacle_clusters.csv", cluster_rows)
    write_csv(out / "obstacle_gt_support.csv", gt_rows)
    (out / "hardware.json").write_text(json.dumps(hardware_info(args.repeats), ensure_ascii=False, indent=2), encoding="utf-8")
    plot_sweeps(rows, out / "figures" / "obstacle_sweep.png")
    print(f"Saved {len(rows)} configurations and {len(latency_rows)} measured runs to {out}")


if __name__ == "__main__":
    main()
