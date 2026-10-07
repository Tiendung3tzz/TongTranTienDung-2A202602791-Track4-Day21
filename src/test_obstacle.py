"""Meaningful geometry, clustering and repeatability checks for the pipeline."""
import unittest
from dataclasses import replace
from src.obstacle import Config, run_pipeline
import numpy as np
from src.evaluation import points_in_box
from starter.kitti_io import KittiObject


class PipelineTests(unittest.TestCase):
    def test_ground_two_objects_and_invalid_points(self):
        gx, gy = np.meshgrid(np.arange(1, 20, .2), np.arange(-5, 5, .2))
        ground = np.column_stack((gx.ravel(), gy.ravel(), np.full(gx.size, -1.7)))
        x, y, z = np.meshgrid(np.arange(8, 8.7, .1), np.arange(-2, -1.5, .1), np.arange(-1.5, -.5, .1))
        one = np.column_stack((x.ravel(), y.ravel(), z.ravel()))
        two = one + [0, 3, 0]
        xyz = np.vstack((ground, one, two, [[np.nan, 0, 0], [np.inf, 0, 0], [-5, 0, -1]]))
        cfg = Config(voxel_size=.1, eps=.3, min_points=5)
        a, b = run_pipeline(xyz, cfg), run_pipeline(xyz, cfg)
        self.assertEqual(a["metrics"]["n_invalid_xyz"], 2)
        self.assertEqual(a["metrics"]["n_clusters"], 2)
        self.assertTrue(np.all(a["obstacles"][:, 2] > -1.6))
        np.testing.assert_allclose(a["plane"], [0, 0, 1, 1.7], atol=1e-6)
        np.testing.assert_array_equal(a["labels"], b["labels"])
        self.assertGreater(a["metrics"]["nearest_m"], 7.9)

    def test_empty_scene_does_not_report_safe(self):
        with self.assertRaisesRegex(ValueError, "ground candidates"):
            run_pipeline(np.empty((0, 4)))

    def test_config_rejects_invalid_values(self):
        for kwargs in ({"eps": 0}, {"voxel_size": float("nan")}, {"min_points": 1}):
            with self.assertRaises(ValueError):
                Config(**kwargs)

    def test_kitti_bottom_center_and_rotation(self):
        obj = KittiObject("Car", 0, 0, 0, np.zeros(4), np.array([2, 1, 4]), np.array([5, 3, 10]), np.pi/2)
        pts = np.array([[5, 2, 10], [5, 3.1, 10], [5, .9, 10], [5, 2, 11.9], [5.6, 2, 10]])
        self.assertEqual(points_in_box(pts, obj).tolist(), [True, False, False, True, False])


if __name__ == "__main__":
    unittest.main()
