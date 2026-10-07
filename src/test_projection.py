"""Numerical CP2 checks: python -m src.test_projection."""
import numpy as np
from starter.datasets import load_frame
from starter.projection import cam_to_image, velo_to_cam, project_velo_to_image


def main():
    fr = load_frame("data/synthetic", "000000")
    pts = np.array([[10., 0, 0], [np.nan, 0, 0], [-10., 0, 0], [10., 50., 0]])
    cam = velo_to_cam(pts, fr["calib"])
    uv, depth, mask = cam_to_image(cam, fr["calib"].P2, fr["image"].shape)
    assert cam.shape == (4, 3)
    assert abs(cam[0, 2] - 9.73) < .01
    assert mask.tolist() == [True, False, False, False]
    assert uv.shape == (1, 2) and depth.shape == (1,)
    np.testing.assert_allclose(uv[0], [614, 175], atol=1)
    for points in (np.empty((0, 3)), np.array([[np.inf, 0., 0.]])):
        u, d, m = cam_to_image(points, fr["calib"].P2, fr["image"].shape)
        assert u.shape == (0, 2) and d.shape == (0,) and not m.any()
    for root, frame, expected in [("data/synthetic", "000000", 3910),
                                  ("data/kitti_mini", "000011", 19946),
                                  ("data/nuscenes_mini_subset", "scene-0103_010", 3120)]:
        fr = load_frame(root, frame)
        _, _, m = project_velo_to_image(fr["points"], fr["calib"], fr["image"].shape)
        assert m.sum() == expected, (root, int(m.sum()), expected)
        print(f"{root}/{frame}: inside_image={m.sum()}")
    print("CP2 self-test passed")


if __name__ == "__main__":
    main()
