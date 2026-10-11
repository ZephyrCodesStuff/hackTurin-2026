import tempfile
import unittest
from pathlib import Path

import numpy as np

from radar import cluster_frame, dbscan, load_radar


class RadarTests(unittest.TestCase):
    def test_clusters_noise_and_signed_velocity(self):
        points = np.array([
            [0, 1, 10, -3, 0], [0, 1.01, 10, -3, 0], [0, .99, 10, -3, 0],
            [0, 5, 30, 7, 0], [0, 5.01, 30, 7, 0], [0, 4.99, 30, 7, 0],
            [0, 100, 100, 100, 0],
        ])
        clusters = cluster_frame(points)
        self.assertEqual(len(clusters), 2)
        self.assertEqual([c['point_count'] for c in clusters], [3, 3])
        self.assertAlmostEqual(clusters[0]['velocity_mps'], -3)
        self.assertAlmostEqual(clusters[1]['x_m'], 5)
        self.assertEqual(cluster_frame([]), [])
        self.assertEqual(cluster_frame(points[:2]), [])

    def test_identical_features_and_border_point(self):
        clusters = cluster_frame(np.array([[0, 1, 2, 3, 0]] * 3))
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]['velocity_spread_mps'], 0)
        # Il primo punto è inizialmente rumore, poi assorbito come bordo.
        labels = dbscan(np.array([[0.], [.4], [.5], [.6]]), eps=.41, min_samples=3)
        self.assertTrue(np.all(labels == 0))

    def test_csv_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'radar.csv'
            header = 'Frame,Time_s,X_m,Y_m,Velocity_mps,Azimuth_deg\n'
            path.write_text(header + '1,0,1,2,-3,0\n')
            self.assertEqual(load_radar(path)[1][0, 3], -3)
            for row in ['1.5,0,1,2,3,0\n', '1,0,nan,2,3,0\n']:
                path.write_text(header + row)
                with self.assertRaises(ValueError):
                    load_radar(path)
            path.write_text(header + '1,0,1,2,3,0\n1,1,1,2,3,0\n')
            with self.assertRaises(ValueError):
                load_radar(path)


if __name__ == '__main__':
    unittest.main()
