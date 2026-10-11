import os
import re
import argparse
import subprocess
import shutil
import cv2
import numpy as np
from PIL import Image

VALID_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.webp', 
    '.tiff', '.tif', '.ppm', '.pgm', '.gif'
}

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]

def compress_with_ffmpeg(input_file, crf=26):
    """Comprime il video generato usando ffmpeg in H.264 se disponibile sul sistema."""
    if not shutil.which("ffmpeg"):
        return False

    temp_file = input_file + ".temp.mp4"
    print("\nFFmpeg rilevato: avvio compressione H.264 ad alta efficienza...")
    
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-vcodec", "libx264",
        "-crf", str(crf),          # 23-28 è un ottimo compromesso tra qualità e peso ridotto
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        temp_file
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.replace(temp_file, input_file)
        print("Compressione FFmpeg completata con successo!")
        return True
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        print(f"Avviso: compressione FFmpeg non riuscita ({e}). Rimane il file originale.")
        return False

def create_video_from_images(folder_path, output_file, fps, start_frame=None, end_frame=None, scale=1.0, max_dim=None):
    if not os.path.isdir(folder_path):
        print(f"Errore: La cartella '{folder_path}' non esiste.")
        return

    image_files = [
        f for f in os.listdir(folder_path) 
        if os.path.splitext(f)[1].lower() in VALID_EXTENSIONS
    ]

    if not image_files:
        print(f"Nessuna immagine supportata trovata in '{folder_path}'.")
        return

    image_files.sort(key=natural_sort_key)

    # Gestione start frame
    start_idx = 0
    if start_frame:
        start_name = os.path.basename(start_frame)
        if start_name in image_files:
            start_idx = image_files.index(start_name)
        else:
            print(f"Errore: Il frame di inizio '{start_name}' non è presente nella cartella.")
            return

    # Gestione end frame
    end_idx = len(image_files) - 1
    if end_frame:
        end_name = os.path.basename(end_frame)
        if end_name in image_files:
            end_idx = image_files.index(end_name)
        else:
            print(f"Errore: Il frame di fine '{end_name}' non è presente nella cartella.")
            return

    if start_idx > end_idx:
        print(f"Errore: Il frame di inizio si trova dopo il frame di fine.")
        return

    image_files = image_files[start_idx:end_idx + 1]

    print(f"Intervallo selezionato: da '{image_files[0]}' a '{image_files[-1]}'")
    print(f"Totale immagini da processare: {len(image_files)}. Inizio elaborazione...")

    video_writer = None
    target_size = None  # (width, height)

    for idx, filename in enumerate(image_files):
        img_path = os.path.join(folder_path, filename)
        
        try:
            with Image.open(img_path) as pil_img:
                pil_img = pil_img.convert('RGB')
                frame = np.array(pil_img)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"Salto '{filename}' (errore di lettura: {e})")
            continue

        h, w, _ = frame.shape

        # Calcolo risoluzione al primo frame valido
        if video_writer is None:
            new_w, new_h = w, h

            # 1. Ridimensionamento tramite fattore di scala
            if scale != 1.0:
                new_w = int(new_w * scale)
                new_h = int(new_h * scale)

            # 2. Limitazione alla dimensione massima (es. max 1920 px)
            if max_dim and max(new_w, new_h) > max_dim:
                ratio = max_dim / max(new_w, new_h)
                new_w = int(new_w * ratio)
                new_h = int(new_h * ratio)

            # FIX SCHERMO VERDE: Larghezza e altezza DEVONO essere pari
            new_w = new_w - (new_w % 2)
            new_h = new_h - (new_h % 2)
            target_size = (new_w, new_h)

            print(f"Risoluzione video impostata a: {target_size[0]}x{target_size[1]}")

            # Tentativo con codec H.264 (avc1), altrimenti fallback su mp4v
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            video_writer = cv2.VideoWriter(output_file, fourcc, fps, target_size)
            if not video_writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(output_file, fourcc, fps, target_size)

        # Adatta il frame alle dimensioni del video
        if (frame.shape[1], frame.shape[0]) != target_size:
            frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)

        video_writer.write(frame)

        if (idx + 1) % 50 == 0 or (idx + 1) == len(image_files):
            print(f"Elaborate {idx + 1}/{len(image_files)} immagini...")

    if video_writer is not None:
        video_writer.release()
        
        orig_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"\nVideo base creato: '{output_file}' ({orig_size_mb:.2f} MB)")

        # Compressione extra tramite FFmpeg se disponibile
        if compress_with_ffmpeg(output_file):
            final_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"Peso finale ridotto a: {final_size_mb:.2f} MB (risparmio del {100 - (final_size_mb/orig_size_mb * 100):.1f}%)")
    else:
        print("Errore: Impossibile creare il video. Nessuna immagine valida letta.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Crea un video partendo da una sequenza di immagini.")
    parser.add_argument("folder", help="Percorso della cartella contenente le immagini")
    parser.add_argument("-o", "--output", required=True, help="Nome/percorso del file video in output (es. output.mp4)")
    parser.add_argument("-f", "--fps", type=float, default=30.0, help="Framerate del video (default: 30)")
    parser.add_argument("--start", help="Nome dell'immagine da cui iniziare (es. frame_0010.png)")
    parser.add_argument("--end", help="Nome dell'immagine con cui finire (es. frame_0500.png)")
    parser.add_argument("--scale", type=float, default=1.0, help="Fattore di scala per ridurre le dimensioni (es. 0.5 per dimezzare)")
    parser.add_argument("--max-dim", type=int, default=None, help="Dimensione massima in pixel del lato più lungo (es. 1920 per Full HD)")

    args = parser.parse_args()
    create_video_from_images(
        args.folder, args.output, args.fps, 
        args.start, args.end, args.scale, args.max_dim
    )