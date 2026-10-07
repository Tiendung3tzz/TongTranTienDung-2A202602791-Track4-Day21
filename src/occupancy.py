"""2D occupied/unknown BEV; absent returns do not imply free space."""
import argparse
from pathlib import Path
from src.obstacle import Config, run_pipeline
import numpy as np
import matplotlib.pyplot as plt
from starter.datasets import load_points, dataset_type
from src.experiment import write_csv


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data/kitti_mini", help="KITTI root")
    ap.add_argument("--frame", default="000011", help="KITTI frame")
    ap.add_argument("--cell-size", type=float, default=.25, help="Grid resolution (m)")
    ap.add_argument("--out-dir", default="results", help="Output directory")
    args = ap.parse_args()
    if dataset_type(args.data_root) != "kitti":
        ap.error("Requires KITTI LiDAR axes (x forward, y left, z up)")
    if not np.isfinite(args.cell_size) or args.cell_size <= 0:
        ap.error("cell-size must be finite and > 0")
    cfg = Config()
    result = run_pipeline(load_points(args.data_root, args.frame), cfg)
    pts = result["obstacles"]
    xedges = np.arange(0, cfg.max_forward + args.cell_size, args.cell_size)
    yedges = np.arange(-cfg.half_width, cfg.half_width + args.cell_size, args.cell_size)
    hist, _, _ = np.histogram2d(pts[:, 0], pts[:, 1], bins=[xedges, yedges])
    occupied = hist > 0
    ix, iy = np.where(occupied)
    out = Path(args.out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    rows = [{"frame": args.frame, "cell_size_m": args.cell_size,
             "x_min_m": xedges[x], "y_min_m": yedges[y], "obstacle_points": int(hist[x, y])} for x, y in zip(ix, iy)]
    write_csv(out / f"occupancy_{args.frame}.csv", rows)
    fig, ax = plt.subplots(figsize=(7, 8), constrained_layout=True)
    ax.imshow(occupied, origin="lower", cmap="Greys", vmin=0, vmax=1,
              extent=[yedges[0], yedges[-1], xedges[0], xedges[-1]], interpolation="nearest")
    ax.set(xlabel="LiDAR y / left (m)", ylabel="LiDAR x / forward (m)",
           title=f"KITTI {args.frame}: occupied cells ({args.cell_size} m)\nBlack = observed obstacle; white = unknown")
    fig.savefig(out / "figures" / f"occupancy_{args.frame}.png", dpi=160)
    plt.close(fig)
    print(f"{int(occupied.sum())} occupied cells; unknown cells are not safe/free")


if __name__ == "__main__":
    main()
