"""Tracking leggero: python3 tracking.py video.mp4 modello.onnx --output tracking.mp4"""
import argparse
import colorsys
import math
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from benchmark import load_model, preprocess, decode, label


def center(box):
    return (box[:2] + box[2:]) / 2


def overlap(a, b):
    """IoU: area di intersezione divisa per area di unione."""
    intersection = np.maximum(0, np.minimum(a[2:], b[2:]) - np.maximum(a[:2], b[:2])).prod()
    union = (a[2:] - a[:2]).prod() + (b[2:] - b[:2]).prod() - intersection
    return float(intersection / union) if union > 0 else 0.


class Tracker:
    def __init__(self, max_missing=10, trail_length=60, max_distance=1.0):
        self.tracks = {}
        self.next_id = 1
        self.max_missing = max_missing
        self.trail_length = trail_length
        self.max_distance = max_distance

    def update(self, detections):
        boxes = [np.array(d['bbox_xyxy_px'], dtype=float) for d in detections]
        candidates = []
        for track_id, track in self.tracks.items():
            # La velocità è in pixel/frame, misurata tra gli ultimi rilevamenti.
            gap = track['missing'] + 1
            shift = track['velocity'] * gap
            predicted = track['box'] + np.tile(shift, 2)
            for index, (detection, box) in enumerate(zip(detections, boxes)):
                if detection['class_id'] != track['detection']['class_id']:
                    continue
                # Normalizzazione rispetto alla box: tollera oggetti che si avvicinano.
                size = max(np.linalg.norm(predicted[2:] - predicted[:2]),
                           np.linalg.norm(box[2:] - box[:2]), 1.)
                distance = np.linalg.norm(center(box) - center(predicted)) / size
                iou = overlap(predicted, box)
                if distance <= self.max_distance and (iou > 0.05 or distance < 0.5):
                    cost = (1 - iou) + distance + 0.05 * track['missing']
                    candidates.append((cost, track_id, index))

        # Associazione greedy uno-a-uno, dal costo minore al maggiore.
        used_tracks, used_detections = set(), set()
        for _, track_id, index in sorted(candidates):
            if track_id in used_tracks or index in used_detections:
                continue
            track = self.tracks[track_id]
            gap = track['missing'] + 1
            velocity = (center(boxes[index]) - center(track['box'])) / gap
            track['velocity'] = 0.5 * track['velocity'] + 0.5 * velocity
            track['box'] = boxes[index]
            track['detection'] = detections[index]
            track['missing'] = 0
            used_tracks.add(track_id)
            used_detections.add(index)

        for track_id in list(self.tracks):
            if track_id not in used_tracks:
                self.tracks[track_id]['missing'] += 1
                if self.tracks[track_id]['missing'] > self.max_missing:
                    del self.tracks[track_id]

        for index, detection in enumerate(detections):
            if index not in used_detections:
                self.tracks[self.next_id] = {
                    'box': boxes[index], 'detection': detection,
                    'velocity': np.zeros(2), 'missing': 0,
                    'trail': deque(maxlen=self.trail_length),
                }
                self.next_id += 1

        for track in self.tracks.values():
            # None interrompe la linea durante un'occlusione: niente punti inventati.
            box = track['box']
            point = (round((box[0] + box[2]) / 2), round(box[3]))
            track['trail'].append(point if track['missing'] == 0 else None)
        return self.tracks


def draw_tracks(frame, tracks):
    for track_id, track in tracks.items():
        if track['missing']:
            continue  # Conservato in memoria, ma non disegnato quando non rilevato.
        rgb = colorsys.hsv_to_rgb((track_id * 0.618034) % 1, 0.75, 0.8)
        color = tuple(round(c * 255) for c in rgb[::-1])
        points = list(track['trail'])
        for previous, current in zip(points, points[1:]):
            if previous is not None and current is not None:
                cv2.line(frame, previous, current, color, 2, cv2.LINE_AA)
        if points and points[-1] is not None:
            cv2.circle(frame, points[-1], 3, color, -1, cv2.LINE_AA)
        x1, y1, x2, y2 = np.rint(track['box']).astype(int)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
        detection = track['detection']
        text = f"#{track_id} {detection['type']} {detection['confidence']:.1%}"
        label(frame, text, x1, y1 - 30, color)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('model', type=Path)
    parser.add_argument('--output', type=Path, default=Path('tracking.mp4'))
    parser.add_argument('--confidence', type=float, default=0.25)
    parser.add_argument('--iou', type=float, default=0.45, help='Soglia NMS del detector')
    parser.add_argument('--max-missing', type=int, default=10, help='Frame assenti tollerati prima di eliminare un ID')
    parser.add_argument('--trail-length', type=int, default=60, help='Lunghezza massima della scia in frame')
    parser.add_argument('--max-distance', type=float, default=1.0, help='Distanza massima di associazione in diagonali della box')
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if not args.video.is_file() or not args.model.is_file():
        parser.error('Video o modello inesistente.')
    if args.output.exists():
        parser.error('Il file output esiste già: scegli un altro percorso.')
    if args.output.suffix.lower() != '.mp4':
        parser.error('Usa un file output .mp4.')
    if not (0 < args.confidence < 1 and 0 < args.iou < 1
            and math.isfinite(args.max_distance) and args.max_distance > 0
            and args.max_missing >= 0 and args.trail_length >= 2 and args.threads > 0):
        parser.error('Soglie in (0,1), distanza/threads > 0, max-missing >= 0, trail-length >= 2.')

    cv2.setNumThreads(args.threads)
    net, names, size = load_model(args.model)
    tracker = Tracker(args.max_missing, args.trail_length, args.max_distance)
    cap = cv2.VideoCapture(str(args.video))
    writer = None
    count = 0
    try:
        if not cap.isOpened():
            raise ValueError('Impossibile aprire il video.')
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError('FPS del video non validi.')
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if writer is None:
                h, w = frame.shape[:2]
                # I codec MP4 richiedono dimensioni pari: eventuale bordo di 1 pixel.
                output_size = (w + w % 2, h + h % 2)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*'mp4v'), fps, output_size)
                if not writer.isOpened():
                    raise OSError('Impossibile creare il video MP4 con il codec mp4v.')
            blob, transform = preprocess(frame, size)
            net.setInput(blob)
            detections = decode(net.forward(), names, transform, frame.shape, args.confidence, args.iou)
            draw_tracks(frame, tracker.update(detections))
            h, w = frame.shape[:2]
            if (w + w % 2, h + h % 2) != output_size:
                raise ValueError('La risoluzione del video cambia durante la lettura.')
            frame = cv2.copyMakeBorder(frame, 0, h % 2, 0, w % 2, cv2.BORDER_CONSTANT)
            writer.write(frame)
            count += 1
            if count % 100 == 0:
                print(f'{count} frame elaborati', flush=True)
        if count == 0:
            raise ValueError('Nessun frame decodificabile nel video.')
    finally:
        cap.release()
        if writer is not None:
            writer.release()
    print(f'Video: {args.output} | {count} frame | {tracker.next_id - 1} ID assegnati')


if __name__ == '__main__':
    main()
