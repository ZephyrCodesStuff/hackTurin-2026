"""Elabora un'immagine con un modello ONNX e salva frame annotato e JSON."""
import argparse
import colorsys
import json
import math
from pathlib import Path
from time import perf_counter

import cv2

from benchmark import load_model, preprocess, decode, calculate_vehicle_location, annotate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path, help='Percorso del modello ONNX YOLO')
    parser.add_argument('frame', type=Path, help='Immagine da elaborare, ad esempio JPG o PNG')
    parser.add_argument('--output', type=Path, default=Path('output_frame'))
    parser.add_argument('--confidence', type=float, default=0.25)
    parser.add_argument('--iou', type=float, default=0.45)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--cam-x', type=float, default=0)
    parser.add_argument('--cam-y', type=float, default=0)
    parser.add_argument('--cam-height', type=float, default=3)
    parser.add_argument('--cam-pitch', type=float, default=30)
    parser.add_argument('--vfov', type=float, default=73.74)
    args = parser.parse_args()

    if not args.model.is_file() or not args.frame.is_file():
        parser.error('Modello o immagine inesistente.')
    values = [args.confidence, args.iou, args.cam_x, args.cam_y,
              args.cam_height, args.cam_pitch, args.vfov]
    if not all(math.isfinite(v) for v in values):
        parser.error('I parametri devono essere finiti.')
    if not (0 < args.confidence < 1 and 0 < args.iou < 1 and args.threads > 0
            and args.cam_height > 0 and 0 <= args.cam_pitch < 90 and 0 < args.vfov < 180):
        parser.error('Soglie in (0,1), threads/altezza > 0, pitch in [0,90), FOV in (0,180).')
    if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
        parser.error('Scegli una cartella output nuova o vuota.')

    cv2.setNumThreads(args.threads)
    t0 = perf_counter()
    frame = cv2.imread(str(args.frame), cv2.IMREAD_COLOR)
    if frame is None:
        parser.error('Immagine non leggibile da OpenCV.')
    t1 = perf_counter()
    net, names, size = load_model(args.model)
    t2 = perf_counter()
    blob, transform = preprocess(frame, size)
    t3 = perf_counter()
    # Una sola inferenza: il tempo include l'inizializzazione della prima forward.
    net.setInput(blob)
    output = net.forward()
    t4 = perf_counter()
    objects = decode(output, names, transform, frame.shape, args.confidence, args.iou)
    camera = dict(x_m=args.cam_x, y_m=args.cam_y, height_m=args.cam_height,
                  pitch_deg=args.cam_pitch, vfov_deg=args.vfov)
    groups = {name: {'count': 0, 'mean_confidence': None} for name in names}
    for obj in objects:
        x1, y1, x2, y2 = obj['bbox_xyxy_px']
        obj['world_xy_m'] = calculate_vehicle_location(
            (x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1, frame.shape[1], frame.shape[0], camera)
        group = groups[obj['type']]
        group['count'] += 1
        group['mean_confidence'] = (group['mean_confidence'] or 0) + obj['confidence']
    for group in groups.values():
        if group['count']:
            group['mean_confidence'] /= group['count']
    t5 = perf_counter()

    colors = [tuple(round(c * 255) for c in colorsys.hsv_to_rgb(i / len(names), .8, .65)[::-1])
              for i in range(len(names))]
    for obj in objects:
        annotate(frame, obj, colors)
    t6 = perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    image_path = args.output / 'frame.png'
    if not cv2.imwrite(str(image_path), frame):
        raise OSError(f'Impossibile salvare {image_path}')
    t7 = perf_counter()

    result = {
        'metadata': {
            'model': str(args.model), 'source_image': str(args.frame),
            'classes': names, 'input_size_wh': size, 'camera': camera,
            'confidence_threshold': args.confidence, 'nms_iou': args.iou,
            'backend': 'OpenCV CPU', 'opencv_version': cv2.__version__,
            'threads': args.threads, 'warmup_runs': 0,
            'confidence_note': 'Confidenza del modello, non accuratezza misurata.',
            'coordinates_note': 'Stima sul piano stradale con la formula fornita e bbox visibile.',
        },
        'image': 'frame.png',
        'size_wh': [frame.shape[1], frame.shape[0]],
        'counts_by_type': groups,
        'objects': objects,
        'timing': {
            'read_ms': (t1-t0)*1000, 'model_load_ms': (t2-t1)*1000,
            'preprocess_ms': (t3-t2)*1000, 'inference_ms': (t4-t3)*1000,
            'postprocess_ms': (t5-t4)*1000, 'draw_ms': (t6-t5)*1000,
            'save_ms': (t7-t6)*1000, 'processing_ms': (t5-t2)*1000,
            'total_before_json_ms': (t7-t0)*1000,
        },
    }
    json_path = args.output / 'results.json'
    with json_path.open('w', encoding='utf-8') as log:
        json.dump(result, log, ensure_ascii=False, indent=2, allow_nan=False)
        log.write('\n')
    print(f'{len(objects)} oggetti rilevati')
    print(f'Frame: {image_path}')
    print(f'JSON: {json_path}')


if __name__ == '__main__':
    main()
