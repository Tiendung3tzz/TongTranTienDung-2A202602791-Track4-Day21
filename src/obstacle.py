"""Topic D: finite/ROI -> voxel -> RANSAC ground -> DBSCAN -> AABBs.

Uses documented Open3D APIs (no copied source):
https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html
All distances are metres in KITTI LiDAR coordinates: x forward, y left, z up.
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", ".cache/matplotlib")

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import open3d as o3d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from starter.datasets import load_points, dataset_type


@dataclass(frozen=True)
class Config:
    voxel_size: float = .15
    distance_threshold: float = .1
    eps: float = .5
    min_points: int = 10
    seed: int = 42
    max_forward: float = 40.
    half_width: float = 15.

    def __post_init__(self):
        for key in ("voxel_size", "distance_threshold", "eps", "max_forward", "half_width"):
            if not np.isfinite(getattr(self, key)) or getattr(self, key) <= 0:
                raise ValueError(f"{key} must be finite and > 0")
        if self.min_points < 3:
            raise ValueError("min_points must be >= 3")


def cloud(xyz):
    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(np.asarray(xyz, dtype=np.float64))
    return pc


def run_pipeline(points: np.ndarray, cfg: Config = Config()) -> dict:
    """No file IO/plotting. Raises on missing ground rather than reporting safe space."""
    xyz = np.asarray(points[:, :3], dtype=np.float64)
    finite = np.isfinite(xyz).all(axis=1)
    roi_mask = (finite & (xyz[:, 0] >= 1) & (xyz[:, 0] <= cfg.max_forward)
                & (np.abs(xyz[:, 1]) <= cfg.half_width)
                & (xyz[:, 2] >= -3) & (xyz[:, 2] <= 2))
    roi = xyz[roi_mask]
    voxel = np.asarray(cloud(roi).voxel_down_sample(cfg.voxel_size).points)
    # KITTI road is usually ~1.7 m below the LiDAR. Fit lower points only,
    # then classify ALL voxel points. This avoids fitting a large vertical wall.
    candidates = voxel[voxel[:, 2] < -.8]
    if len(candidates) < 3:
        raise ValueError("Insufficient ground candidates: cannot certify free space")
    o3d.utility.random.seed(cfg.seed)
    plane, _ = cloud(candidates).segment_plane(
        distance_threshold=cfg.distance_threshold, ransac_n=3,
        num_iterations=300, probability=.999)
    plane = np.asarray(plane, dtype=float)
    plane /= np.linalg.norm(plane[:3])
    if plane[2] < 0:
        plane *= -1
    if plane[2] < np.cos(np.deg2rad(20)):
        raise ValueError("RANSAC plane is not a ground plane (tilt > 20 degrees)")
    height = voxel @ plane[:3] + plane[3]
    above_ground = height > cfg.distance_threshold
    obstacles = voxel[above_ground]
    labels = (np.asarray(cloud(obstacles).cluster_dbscan(
        eps=cfg.eps, min_points=cfg.min_points, print_progress=False))
        if len(obstacles) else np.empty(0, dtype=int))
    boxes = []
    for cluster_id in np.unique(labels[labels >= 0]):
        pts = obstacles[labels == cluster_id]
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        # Distance from ego origin to nearest point of the XY AABB footprint.
        closest = np.maximum(np.maximum(lo[:2], -hi[:2]), 0)
        boxes.append({"cluster_id": int(cluster_id), "n_points": len(pts),
                      "lo": lo, "hi": hi, "extent": hi - lo,
                      "nearest_m": float(np.linalg.norm(closest))})
    extents = np.asarray([b["extent"] for b in boxes])
    metrics = {"n_input": len(points), "n_invalid_xyz": int((~finite).sum()),
               "n_roi": len(roi), "n_voxel": len(voxel),
               "n_removed": int((~above_ground).sum()), "n_obstacle": len(obstacles),
               "n_noise": int((labels < 0).sum()), "n_clusters": len(boxes),
               "nearest_m": min((b["nearest_m"] for b in boxes), default=float("nan")),
               "median_length_m": float(np.median(extents[:, 0])) if len(boxes) else float("nan"),
               "median_width_m": float(np.median(extents[:, 1])) if len(boxes) else float("nan"),
               "median_height_m": float(np.median(extents[:, 2])) if len(boxes) else float("nan")}
    return {"roi": roi, "voxel": voxel, "plane": plane, "height": height,
            "above_ground": above_ground, "obstacles": obstacles,
            "labels": labels, "boxes": boxes, "metrics": metrics}


def style_bev(ax, cfg, title):
    ax.set(xlim=(-cfg.half_width, cfg.half_width), ylim=(0, cfg.max_forward),
           xlabel="LiDAR y / left (m)", ylabel="LiDAR x / forward (m)", title=title)
    ax.set_aspect("equal")
    ax.grid(alpha=.2)
    ax.scatter([0], [0], c="black", marker="^", s=50)


def plot_clusters(ax, result, cfg, title="DBSCAN + obstacle boxes"):
    labels, xyz = result["labels"], result["obstacles"]
    ax.scatter(xyz[:, 1], xyz[:, 0], s=1, c=labels, cmap="tab20", vmin=-1,
               vmax=max(20, int(labels.max()) if len(labels) else 20), rasterized=True)
    for box in result["boxes"]:
        lo, hi = box["lo"], box["hi"]
        ax.add_patch(Rectangle((lo[1], lo[0]), hi[1]-lo[1], hi[0]-lo[0],
                               fill=False, edgecolor="#d63838", lw=.8))
    style_bev(ax, cfg, f"{title}\n{len(result['boxes'])} clusters")


def save_demo(result, cfg, frame, out):
    fig, axes = plt.subplots(1, 4, figsize=(15, 6), constrained_layout=True)
    for ax, key, title in zip(axes[:2], ("roi", "voxel"), ("Finite points in ROI", "Voxel downsample")):
        pts = result[key]
        ax.scatter(pts[:, 1], pts[:, 0], s=.5, c=pts[:, 2], cmap="viridis", rasterized=True)
        style_bev(ax, cfg, f"{title}\n{len(pts):,} points")
    pts = result["voxel"]
    axes[2].scatter(pts[:, 1], pts[:, 0], s=1,
                    c=np.where(result["above_ground"], "#cb3939", "#c4ced7"), rasterized=True)
    style_bev(axes[2], cfg, f"RANSAC: red = retained\n{len(result['obstacles']):,} obstacle points")
    plot_clusters(axes[3], result, cfg)
    fig.suptitle(f"KITTI {frame} | voxel={cfg.voxel_size} m | ground={cfg.distance_threshold} m | eps={cfg.eps} m", fontsize=14)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)


def add_config_args(ap):
    ap.add_argument("--voxel-size", type=float, default=.15, help="Voxel edge length in metres")
    ap.add_argument("--distance-threshold", type=float, default=.1, help="RANSAC ground band width in metres")
    ap.add_argument("--eps", type=float, default=.5, help="DBSCAN neighbourhood radius in metres")
    ap.add_argument("--min-points", type=int, default=10, help="DBSCAN minimum neighbourhood size")
    ap.add_argument("--seed", type=int, default=42, help="Open3D RANSAC random seed")


def config_from_args(args):
    return Config(args.voxel_size, args.distance_threshold, args.eps, args.min_points, args.seed)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data/kitti_mini", help="KITTI data root; KITTI axes required")
    ap.add_argument("--frame", default="000011", help="KITTI frame ID")
    ap.add_argument("--out", default="results/figures/obstacle_demo_000011.png", help="Output PNG")
    add_config_args(ap)
    args = ap.parse_args()
    if dataset_type(args.data_root) != "kitti":
        ap.error("Requires KITTI LiDAR axes (x forward, y left, z up)")
    cfg = config_from_args(args)
    result = run_pipeline(load_points(args.data_root, args.frame), cfg)
    save_demo(result, cfg, args.frame, args.out)
    print({**asdict(cfg), **result["metrics"]})
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
