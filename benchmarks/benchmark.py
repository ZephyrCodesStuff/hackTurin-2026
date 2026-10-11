"""Benchmark OpenCV di modelli ONNX YOLO detection, un frame alla volta."""
import argparse
import ast
import colorsys
import json
import io
import math
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np


def calculate_vehicle_location(cx, cy, width, height, img_width, img_height, camera):
    """Formula richiesta: punto inferiore della box proiettato sulla strada (metri)."""
    focal = (img_height / 2) / math.tan(math.radians(camera['vfov_deg']) / 2)
    alpha_y = math.atan2(cy + height / 2 - img_height / 2, focal)
    alpha_x = math.atan2(cx - img_width / 2, focal)
    angle = math.radians(camera['pitch_deg']) + alpha_y
    if angle <= 0 or angle >= math.pi / 2:
        return None
    forward = camera['height_m'] / math.tan(angle)
    return {'x': camera['x_m'] + forward * math.tan(alpha_x),
            'y': camera['y_m'] + forward}


def protobuf_fields(stream):
    """Legge i campi protobuf ONNX; salta i pesi senza caricarli in RAM."""
    def varint():
        value, shift = 0, 0
        while shift < 70:
            byte = stream.read(1)
            if not byte:
                raise ValueError('File ONNX troncato.')
            value |= (byte[0] & 127) << shift
            if byte[0] < 128:
                return value
            shift += 7
        raise ValueError('Intero protobuf non valido.')

    while stream.read(1):
        stream.seek(-1, 1)
        tag = varint()
        field, wire = tag >> 3, tag & 7
        if wire == 2:
            length = varint()
            position = stream.tell()
            yield field, length
            stream.seek(position + length)
        elif wire == 0:
            varint()
        elif wire in (1, 5):
            stream.seek(8 if wire == 1 else 4, 1)
        else:
            raise ValueError('Formato protobuf non supportato.')


def load_model(path):
    """Legge solo metadata_props (campo 14 del formato ONNX)."""
    metadata = {}
    with path.open('rb') as stream:
        for field, length in protobuf_fields(stream):
            if field == 14:
                entry = io.BytesIO(stream.read(length))
                parts = {}
                for key, size in protobuf_fields(entry):
                    parts[key] = entry.read(size).decode('utf-8')
                metadata[parts[1]] = parts[2]
    if metadata.get('task') != 'detect':
        raise ValueError('Serve un ONNX YOLO con metadati task=detect.')
    names = ast.literal_eval(metadata.get('names', '{}'))
    dimensions = ast.literal_eval(metadata.get('imgsz', '[]'))
    if not names or len(dimensions) != 2 or min(dimensions) <= 0:
        raise ValueError('Servono metadati YOLO names e imgsz validi.')
    if metadata.get('batch', '1') != '1' or metadata.get('channels', '3') != '3':
        raise ValueError('Supportati solo batch=1 e 3 canali RGB.')
    names = [names[i] for i in range(len(names))]
    size = (dimensions[1], dimensions[0])
    net = cv2.dnn.readNetFromONNX(str(path))
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    if len(net.getUnconnectedOutLayersNames()) != 1:
        raise ValueError('Supportato un solo output YOLO detection senza NMS incorporata.')
    return net, names, size


def preprocess(frame, size):
    """Letterbox: ridimensiona senza deformare e aggiunge bordi grigi."""
    h, w = frame.shape[:2]
    scale = min(size[0] / w, size[1] / h)
    rw, rh = round(w * scale), round(h * scale)
    left, top = (size[0] - rw) // 2, (size[1] - rh) // 2
    resized = cv2.resize(frame, (rw, rh))
    padded = cv2.copyMakeBorder(resized, top, size[1] - rh - top,
                               left, size[0] - rw - left, cv2.BORDER_CONSTANT,
                               value=(114, 114, 114))
    blob = cv2.dnn.blobFromImage(padded, 1 / 255, size, swapRB=True)
    return blob, (rw / w, rh / h, left, top)


def decode(output, names, transform, shape, confidence, iou):
    """YOLO moderno: [1, 4+classi, N]; YOLOv5: [1, N, 5+classi]."""
    nc = len(names)
    if output.ndim != 3 or output.shape[0] != 1:
        raise ValueError(f'Output YOLO non supportato: {output.shape}')
    if output.shape[1] == nc + 4:
        rows = output[0].T
        scores = rows[:, 4:]
    elif output.shape[2] == nc + 5:
        rows = output[0]
        scores = rows[:, 5:] * rows[:, 4:5]
    else:
        raise ValueError(f'Output non supportato: {output.shape}, classi={nc}')
    ids = scores.argmax(axis=1)
    confidences = scores[np.arange(len(rows)), ids]
    mask = (confidences > confidence) & np.isfinite(rows).all(axis=1)
    rows, ids, confidences = rows[mask], ids[mask], confidences[mask]
    sx, sy, left, top = transform
    boxes = rows[:, :4].copy()
    boxes[:, 0] = (rows[:, 0] - rows[:, 2] / 2 - left) / sx
    boxes[:, 1] = (rows[:, 1] - rows[:, 3] / 2 - top) / sy
    boxes[:, 2] /= sx
    boxes[:, 3] /= sy
    detections = []
    h, w = shape[:2]
    # NMS separata per classe: oggetti di tipo diverso non si eliminano tra loro.
    for class_id in np.unique(ids):
        indices = np.flatnonzero(ids == class_id)
        keep = cv2.dnn.NMSBoxes(boxes[indices].tolist(), confidences[indices].tolist(), confidence, iou)
        for index in np.asarray(keep).reshape(-1):
            i = indices[index]
            x, y, bw, bh = map(float, boxes[i])
            x1, y1 = max(0., x), max(0., y)
            x2, y2 = min(float(w), x + bw), min(float(h), y + bh)
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append({'class_id': int(class_id), 'type': names[class_id],
                               'confidence': float(confidences[i]),
                               'bbox_xyxy_px': [x1, y1, x2, y2]})
    return detections


def label(frame, text, x, y, color):
    """Etichetta con fondo arrotondato e testo bianco; resta dentro il frame."""
    font, scale = cv2.FONT_HERSHEY_SIMPLEX, 0.45
    (tw, th), baseline = cv2.getTextSize(text, font, scale, 1)
    h, w = frame.shape[:2]
    if tw + 12 > w:
        scale *= max(1, w - 12) / (tw + 1)
        (tw, th), baseline = cv2.getTextSize(text, font, scale, 1)
    bw, bh, r = tw + 12, th + baseline + 10, 5
    x, y = max(0, min(int(x), w - bw)), max(0, min(int(y), h - bh))
    cv2.rectangle(frame, (x + r, y), (x + bw - r, y + bh), color, -1)
    cv2.rectangle(frame, (x, y + r), (x + bw, y + bh - r), color, -1)
    for cx, cy in [(x+r, y+r), (x+bw-r, y+r), (x+r, y+bh-r), (x+bw-r, y+bh-r)]:
        cv2.circle(frame, (cx, cy), r, color, -1, cv2.LINE_AA)
    cv2.putText(frame, text, (x + 6, y + th + 5), font, scale, (255, 255, 255), 1, cv2.LINE_AA)


def annotate(frame, detection, colors):
    x1, y1, x2, y2 = [round(v) for v in detection['bbox_xyxy_px']]
    color = colors[detection['class_id']]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
    label(frame, f"{detection['type']} {detection['confidence']:.1%}", x1, y1 - 30, color)
    point = detection['world_xy_m']
    text = f"X {point['x']:.2f} m  Y {point['y']:.2f} m" if point else 'Coordinate N/D'
    label(frame, text, x1, y2 + 3, color)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('video', type=Path)
    parser.add_argument('--output', type=Path, default=Path('output'))
    parser.add_argument('--confidence', type=float, default=0.25)
    parser.add_argument('--iou', type=float, default=0.45)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--cam-x', type=float, default=0)
    parser.add_argument('--cam-y', type=float, default=0)
    parser.add_argument('--cam-height', type=float, default=3)
    parser.add_argument('--cam-pitch', type=float, default=30)
    parser.add_argument('--vfov', type=float, default=73.74)
    args = parser.parse_args()
    if not args.model.is_file() or not args.video.is_file():
        parser.error('Modello o video inesistente.')
    values = [args.confidence, args.iou, args.cam_x, args.cam_y, args.cam_height, args.cam_pitch, args.vfov]
    if not all(math.isfinite(v) for v in values):
        parser.error('I parametri devono essere finiti.')
    if not (0 < args.confidence < 1 and 0 < args.iou < 1 and args.threads > 0
            and args.cam_height > 0 and 0 <= args.cam_pitch < 90 and 0 < args.vfov < 180):
        parser.error('Soglie in (0,1), threads/altezza > 0, pitch in [0,90), FOV in (0,180).')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('La cartella output deve essere vuota: scegli --output per un nuovo benchmark.')
    cv2.setNumThreads(args.threads)
    start = perf_counter()
    net, names, size = load_model(args.model)
    load_ms = (perf_counter() - start) * 1000
    camera = dict(x_m=args.cam_x, y_m=args.cam_y, height_m=args.cam_height,
                  pitch_deg=args.cam_pitch, vfov_deg=args.vfov)
    colors = [tuple(round(c * 255) for c in colorsys.hsv_to_rgb(i / len(names), .8, .65)[::-1])
              for i in range(len(names))]
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise ValueError('Impossibile aprire il video.')
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if math.isfinite(fps) and fps > 0 else None
    metadata = dict(model=str(args.model), video=str(args.video), classes=names,
                    input_size_wh=size, camera=camera, video_fps=fps,
                    confidence_threshold=args.confidence, nms_iou=args.iou,
                    backend='OpenCV CPU', opencv_version=cv2.__version__, threads=args.threads,
                    confidence_note='Confidenza del modello, non accuratezza misurata.',
                    coordinates_note='Stima sul piano stradale con la formula fornita e bbox visibile.')
    count, inference_total, processing_total = 0, 0., 0.
    frames_dir = args.output / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    total_start = perf_counter()
    try:
        # Scrittura incrementale: il JSON non viene accumulato in RAM.
        with (args.output / 'results.json').open('w', encoding='utf-8') as log:
            log.write('{"metadata":' + json.dumps(metadata, ensure_ascii=False) + ',"frames":[\n')
            while True:
                t0 = perf_counter()
                ok, frame = cap.read()
                if not ok:
                    break
                t1 = perf_counter()
                blob, transform = preprocess(frame, size)
                if count == 0:
                    # Riscaldamento escluso dai tempi per frame.
                    warm_start = perf_counter()
                    for _ in range(3):
                        net.setInput(blob)
                        net.forward()
                    warmup_ms = (perf_counter() - warm_start) * 1000
                    t0 += warmup_ms / 1000
                    t1 += warmup_ms / 1000
                t2 = perf_counter()
                net.setInput(blob)
                output = net.forward()
                t3 = perf_counter()
                objects = decode(output, names, transform, frame.shape, args.confidence, args.iou)
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
                t4 = perf_counter()
                for obj in objects:
                    annotate(frame, obj, colors)
                t5 = perf_counter()
                filename = f'frames/{count:06d}.jpg'
                if not cv2.imwrite(str(args.output / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                    raise OSError(f'Impossibile scrivere {filename}')
                t6 = perf_counter()
                timing = dict(decode_ms=(t1-t0)*1000, preprocess_ms=(t2-t1)*1000,
                              inference_ms=(t3-t2)*1000, postprocess_ms=(t4-t3)*1000,
                              draw_ms=(t5-t4)*1000, save_ms=(t6-t5)*1000,
                              processing_ms=(t4-t1)*1000, frame_ms=(t6-t0)*1000)
                record = dict(frame_index=count, timestamp_s=count/fps if fps else None,
                              image=filename, size_wh=[frame.shape[1], frame.shape[0]],
                              counts_by_type=groups, objects=objects, timing=timing)
                if count:
                    log.write(',\n')
                json.dump(record, log, ensure_ascii=False, allow_nan=False)
                count += 1
                inference_total += timing['inference_ms']
                processing_total += timing['processing_ms']
            if not count:
                raise ValueError('Il video non contiene frame decodificabili.')
            elapsed = perf_counter() - total_start
            summary = dict(frames=count, model_load_ms=load_ms, warmup_ms=warmup_ms,
                           mean_inference_ms=inference_total/count,
                           inference_fps=1000*count/inference_total,
                           mean_processing_ms=processing_total/count,
                           processing_fps=1000*count/processing_total,
                           elapsed_s=elapsed, wall_fps=count/elapsed)
            log.write('\n],"summary":' + json.dumps(summary) + '}\n')
    finally:
        cap.release()
    print(f"{count} frame salvati in {frames_dir}")
    print(f"JSON: {args.output / 'results.json'}")
    print(f"Inferenza: {summary['mean_inference_ms']:.2f} ms/frame; {summary['inference_fps']:.2f} FPS")


if __name__ == '__main__':
    main()
