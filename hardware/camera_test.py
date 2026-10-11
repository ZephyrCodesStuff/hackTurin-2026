import cv2
import numpy as np
import onnxruntime as ort

def run_video_detection(video_path, model_path, conf_thresh=0.50, nms_thresh=0.45, target_fps=None):
    # 1. Carica il modello con ONNX Runtime (supporto nativo INT8)
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    
    # Rileva automaticamente nome e tipo di dato richiesto in input
    input_info = session.get_inputs()[0]
    input_name = input_info.name
    is_uint8_input = "uint8" in input_info.type

    # 2. Apri il video .mp4
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Errore: Impossibile aprire il video {video_path}")
        return

    # Calcolo del ritardo (in millisecondi) per controllare la velocità di riproduzione
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps <= 0:
        original_fps = 30.0  # fallback se i metadati non hanno l'fps

    # Se l'utente specifica un target_fps usa quello, altrimenti usa l'fps del video
    fps_to_use = target_fps if target_fps is not None else original_fps
    delay_ms = max(1, int(1000 / fps_to_use))

    print(f"FPS video originale: {original_fps:.1f} | FPS riproduzione: {fps_to_use:.1f} (pausa: {delay_ms} ms)")
    print("Riproduzione avviata. Premi 'q' per uscire.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Video terminato.")
            break

        h_orig, w_orig = frame.shape[:2]

        # 3. Preprocessing per il modello (640x640, RGB, CHW)
        img = cv2.resize(frame, (640, 640))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if is_uint8_input:
            img = img.astype(np.uint8)
        else:
            img = img.astype(np.float32) / 255.0

        # Passa dal formato (H, W, C) a (1, C, H, W)
        blob = np.transpose(img, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0)

        # 4. Inferenza
        outputs = session.run(None, {input_name: blob})
        preds = outputs[0]

        # Se l'output ha forma (1, 84, 8400) lo trasponiamo in (8400, 84)
        if preds.shape[1] < preds.shape[2]:
            preds = preds[0].T
        else:
            preds = preds[0]

        # 5. Estrazione coordinate e confidenze
        boxes = preds[:, :4]       # [cx, cy, w, h]
        scores = preds[:, 4:]      # confidenze classi
        class_ids = np.argmax(scores, axis=1)
        confs = np.max(scores, axis=1)

        # Filtro confidenza
        mask = confs > conf_thresh
        v_boxes = boxes[mask]
        v_confs = confs[mask]
        v_classes = class_ids[mask]

        if len(v_boxes) > 0:
            scale_x = w_orig / 640.0
            scale_y = h_orig / 640.0

            # Conversione in [top_left_x, top_left_y, w, h]
            nms_boxes = []
            for b in v_boxes:
                cx, cy, w, h = b
                x = int((cx - w / 2) * scale_x)
                y = int((cy - h / 2) * scale_y)
                w_box = int(w * scale_x)
                h_box = int(h * scale_y)
                nms_boxes.append([x, y, w_box, h_box])

            # Rimozione sovrapposizioni (NMS)
            indices = cv2.dnn.NMSBoxes(nms_boxes, v_confs.tolist(), conf_thresh, nms_thresh)

            if len(indices) > 0:
                for i in np.array(indices).flatten():
                    x, y, w_box, h_box = nms_boxes[i]
                    cls = v_classes[i]
                    conf = v_confs[i]

                    # Disegna il box e il testo
                    cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)
                    label = f"ID: {cls} ({conf:.2f})"
                    cv2.putText(frame, label, (x, max(20, y - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 6. Render a video
        cv2.imshow("Detection in tempo reale", frame)

        # --- MODIFICA CHIAVE: attesa dinamica invece di waitKey(1) ---
        if cv2.waitKey(delay_ms) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    VIDEO_PATH = "/Users/sp/Downloads/rgb-backgrounded.mov"
    MODEL_PATH = "/Users/sp/flir_models/models/rgb.onnx"

    # Esempi di utilizzo:
    # 1. Velocità normale del video:
    # run_video_detection(VIDEO_PATH, MODEL_PATH, conf_thresh=0.50)

    # 2. Rallentato a 10 FPS (molto più lento e comodo da osservare):
    run_video_detection(VIDEO_PATH, MODEL_PATH, conf_thresh=0.50, target_fps=10)