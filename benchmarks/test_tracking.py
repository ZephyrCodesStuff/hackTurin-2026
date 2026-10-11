"""Test del ciclo di vita delle tracce: python3 -m unittest test_tracking.py"""
import unittest

from tracking import Tracker


def detection(x, class_id=0):
    return {'class_id': class_id, 'type': str(class_id), 'confidence': .9,
            'bbox_xyxy_px': [x, 0, x + 20, 40]}


class TrackingTests(unittest.TestCase):
    def test_motion_and_detection_order(self):
        tracker = Tracker()
        tracker.update([detection(0), detection(100)])
        tracks = tracker.update([detection(102), detection(2)])
        self.assertEqual(tracks[1]['box'][0], 2)
        self.assertEqual(tracks[2]['box'][0], 102)
        self.assertEqual(len(tracks), 2)

    def test_occlusion_expiry_and_new_id(self):
        tracker = Tracker(max_missing=2)
        tracker.update([detection(0)])
        tracker.update([])
        self.assertEqual(tracker.tracks[1]['missing'], 1)
        tracks = tracker.update([detection(2)])
        self.assertEqual(list(tracks), [1])
        self.assertIsNone(tracks[1]['trail'][1])
        tracker.update([])
        tracker.update([])
        self.assertIn(1, tracker.tracks)
        tracker.update([])
        self.assertFalse(tracker.tracks)
        self.assertEqual(list(tracker.update([detection(2)])), [2])

    def test_class_distance_and_bounded_trail(self):
        tracker = Tracker(max_missing=0, trail_length=3)
        tracker.update([detection(0)])
        self.assertEqual(list(tracker.update([detection(0, 1)])), [2])
        self.assertEqual(list(tracker.update([detection(500, 1)])), [3])
        for x in range(501, 510):
            tracker.update([detection(x, 1)])
        self.assertEqual(list(tracker.tracks), [3])
        self.assertEqual(len(tracker.tracks[3]['trail']), 3)


if __name__ == '__main__':
    unittest.main()
