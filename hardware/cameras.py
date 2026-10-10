import cv2
import numpy as np
from multiprocessing import Process

def stream_worker(port, model_path, cam_name, conf_thresh=0.50):
    # 1. Carica il modello dedicato per questo stream
    net = cv2.dnn.readNetFromONNX(model_path)

    # 2. Pipeline GStreamer a latenza zero
    pipe = f"tcpserversrc port={port} ! jpegparse ! jpegdec ! videoconvert ! appsink drop=true max-buffers=1 sync=false"
    cap = cv2.VideoCapture(pipe, cv2.CAP_GSTREAMER)

    print(f"[{cam_name}] Avviato su porta {port} con {model_path}")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        h_orig, w_orig = frame.shape[:2]

        # Inferenza hardware
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True)
        net.setInput(blob)
        preds = net.forward()[0].T

        # Estrazione vettoriale con NumPy (nessun loop lento)
        boxes = preds[:, :4]
        scores = preds[:, 4:]
        class_ids = np.argmax(scores, axis=1)
        confs = np.max(scores, axis=1)

        # Filtro soglia e rimozione duplicati (NMS)
        mask = confs > conf_thresh
        v_boxes, v_confs, v_classes = boxes[mask], confs[mask], class_ids[mask]
        indices = cv2.dnn.NMSBoxes(v_boxes.tolist(), v_confs.tolist(), conf_thresh, 0.45)

        # Rimappatura pixel centro (cx, cy)
        scale_x, scale_y = w_orig / 640, h_orig / 640
        for i in indices:
            cx = int(v_boxes[i][0] * scale_x)
            cy = int(v_boxes[i][1] * scale_y)
            cls = v_classes[i]
            conf = v_confs[i]

            print(f"[{cam_name}] ID:{cls} ({conf:.2f}) -> CENTRO PIXEL: X={cx}, Y={cy}")

if __name__ == "__main__":
    # Avvia i due stream in parallelo su core CPU separati
    p1 = Process(target=stream_worker, args=(5000, "modello1.onnx", "STREAM_1"))
    p2 = Process(target=stream_worker, args=(5001, "modello2.onnx", "STREAM_2"))

    p1.start()
    p2.start()
    p1.join()
    p2.join()
