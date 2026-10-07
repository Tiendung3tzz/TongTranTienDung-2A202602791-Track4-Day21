"""GT support diagnostics; these are not detection precision/recall."""
import numpy as np
from starter.projection import velo_to_cam, box3d_corners_cam


def points_in_box(points_cam, obj):
    h, w, length = obj.dimensions
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    rotation = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    local = (points_cam - obj.location) @ rotation
    return ((np.abs(local[:, 0]) <= length/2) & (local[:, 1] >= -h)
            & (local[:, 1] <= 0) & (np.abs(local[:, 2]) <= w/2))


def gt_support(fr, result):
    voxel_cam = velo_to_cam(result["voxel"], fr["calib"])
    ids = np.full(len(voxel_cam), -1, dtype=int)
    ids[result["above_ground"]] = result["labels"]
    rows = []
    for index, obj in enumerate(fr["labels"]):
        inside = points_in_box(voxel_cam, obj)
        n = int(inside.sum())
        clusters, counts = np.unique(ids[inside & (ids >= 0)], return_counts=True)
        dominant = int(clusters[np.argmax(counts)]) if len(clusters) else -1
        rows.append({"object_index": index, "class": obj.type,
                     "distance_cam_m": float(np.linalg.norm(obj.location[[0, 2]])),
                     "n_gt_voxel": n, "n_gt_retained": int((inside & result["above_ground"]).sum()),
                     "n_gt_clustered": int((inside & (ids >= 0)).sum()),
                     "dominant_cluster": dominant,
                     "dominant_points": int(counts.max()) if len(counts) else 0})
    return rows


def corners_velo(obj, calib):
    corners = box3d_corners_cam(obj)
    return (np.column_stack((corners, np.ones(8))) @ np.linalg.inv(calib.T_cam_velo).T)[:, :3]
