"""Reproduce and quantify DBSCAN merging two distinct KITTI labelled objects."""
from __future__ import annotations
import argparse
import itertools
import json
from dataclasses import replace, asdict
from pathlib import Path
from src.obstacle import Config, run_pipeline
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from starter.datasets import load_frame
from src.evaluation import gt_support, corners_velo
from src.experiment import write_csv


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data/kitti_mini", help="KITTI root")
    ap.add_argument("--frame", default="000011", help="Frame with adjacent pedestrians")
    ap.add_argument("--baseline-eps", type=float, default=.5, help="Separated-cluster configuration (m)")
    ap.add_argument("--failure-eps", type=float, default=.8, help="Merged-cluster configuration (m)")
    ap.add_argument("--min-points", type=int, default=5, help="Fixed in both configs; 5 supports the sparse pedestrian")
    ap.add_argument("--out-dir", default="results", help="CSV, JSON and failure PNG directory")
    args = ap.parse_args()
    fr = load_frame(args.data_root, args.frame)
    configs = [Config(eps=args.baseline_eps, min_points=args.min_points), Config(eps=args.failure_eps, min_points=args.min_points)]
    results = [run_pipeline(fr["points"], c) for c in configs]
    support = [gt_support(fr, r) for r in results]
    candidates = []
    for i, j in itertools.combinations(range(len(fr["labels"])), 2):
        a, b = support[0][i], support[0][j]
        c, d = support[1][i], support[1][j]
        if (min(a["dominant_points"], b["dominant_points"], c["dominant_points"], d["dominant_points"]) >= 5
                and a["dominant_cluster"] != b["dominant_cluster"]
                and c["dominant_cluster"] == d["dominant_cluster"]):
            candidates.append((i, j))
    if not candidates:
        raise RuntimeError("No verified merge with >=5 GT support points per object; choose another frame/eps")
    pair = next((p for p in candidates if all(fr["labels"][i].type == "Pedestrian" for i in p)), candidates[0])
    out = Path(args.out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    rows = [{"frame": args.frame, "eps": cfg.eps, **s[i]} for cfg, s in zip(configs, support) for i in pair]
    write_csv(out / "failure_merge.csv", rows)
    corners = [corners_velo(fr["labels"][i], fr["calib"]) for i in pair]
    bounds = np.vstack(corners)
    xlim = (float(bounds[:, 1].min()-1), float(bounds[:, 1].max()+1))
    ylim = (float(bounds[:, 0].min()-1), float(bounds[:, 0].max()+1))
    fig, axes = plt.subplots(1, 2, figsize=(11, 6), constrained_layout=True)
    for ax, cfg, result, support_rows in zip(axes, configs, results, support):
        pts, labels = result["obstacles"], result["labels"]
        ax.scatter(pts[:, 1], pts[:, 0], c=labels, cmap="tab20", vmin=-1,
                   vmax=max(20, int(labels.max())), s=15)
        for i, cor in zip(pair, corners):
            poly = np.column_stack((cor[:4, 1], cor[:4, 0]))
            ax.add_patch(Polygon(poly, fill=False, edgecolor="#11854d", lw=2, linestyle="--"))
            center = cor[:4].mean(axis=0)
            ax.annotate(f"GT #{i}", (center[1], center[0]),
                         xytext=(5, 7), textcoords="offset points", fontsize=10)
        ids = {support_rows[i]["dominant_cluster"] for i in pair}
        for box in result["boxes"]:
            if box["cluster_id"] in ids:
                lo, hi = box["lo"], box["hi"]
                ax.add_patch(Rectangle((lo[1], lo[0]), hi[1]-lo[1], hi[0]-lo[0],
                                       fill=False, edgecolor="#ca2f32", lw=2))
        desc = " | ".join(f"GT #{i}: C{support_rows[i]['dominant_cluster']} ({support_rows[i]['dominant_points']} pts)" for i in pair)
        ax.set(title=f"eps={cfg.eps} m\n{desc}", xlim=xlim, ylim=ylim,
               xlabel="LiDAR y / left (m)", ylabel="LiDAR x / forward (m)")
        ax.set_aspect("equal")
        ax.grid(alpha=.2)
    fig.suptitle(f"KITTI {args.frame}: two GT objects share one dominant cluster\nmin_points={args.min_points} | voxel=0.15 m | RANSAC=0.1 m\nGreen dashed = GT footprint; red = cluster AABB", fontsize=14)
    path = out / "figures" / "fail_01_dbscan_merge_pedestrians.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    summary = {"frame": args.frame, "object_indices": list(pair),
               "baseline": asdict(configs[0]), "failure": asdict(configs[1]),
               "support": rows, "debug_layer": "Preprocess", "figure": path.as_posix()}
    (out / "failure_merge.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
