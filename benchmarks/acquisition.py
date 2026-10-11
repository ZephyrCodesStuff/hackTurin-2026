
import os
import subprocess
from pathlib import Path

# Usa le librerie locali preparate in precedenza sulla scheda.
cartella = Path(__file__).resolve().parent
os.environ["GI_TYPELIB_PATH"] = str(
    cartella / ".camera-deps/usr/lib/aarch64-linux-gnu/girepository-1.0"
) + os.pathsep + os.environ.get("GI_TYPELIB_PATH", "")

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import cv2
import numpy as np


def main():
    Gst.init(None)

    # Acquisisce dalla fotocamera del Media Carrier.
    camera = Gst.parse_launch(
        "libcamerasrc ! "
        "video/x-raw,width=1280,height=720 ! "
        "videoconvert ! video/x-raw,format=BGR ! "
        "appsink name=foto max-buffers=1 drop=true sync=false"
    )
    uscita = camera.get_by_name("foto")

    try:
        if camera.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("Impossibile avviare la fotocamera")

        # Aspetta un'immagine, al massimo per 10 secondi.
        foto = uscita.emit("try-pull-sample", 10 * Gst.SECOND)
        if foto is None:
            raise RuntimeError("La fotocamera non ha restituito un'immagine")

        buffer = foto.get_buffer()
        pixels = buffer.extract_dup(0, buffer.get_size())
        immagine = np.frombuffer(pixels, dtype=np.uint8).reshape(720, 1280, 3)

        if not cv2.imwrite("in_img.png", immagine):
            raise RuntimeError("Impossibile salvare in_img.png")
    finally:
        camera.set_state(Gst.State.NULL)

    # Esegue il benchmark sulla foto appena salvata.
    subprocess.run(
        [
            "python3", "benchmark_frame.py",
            "models/data2/rgb.onnx",
            "in_img.png",
            "--output", "out",
        ],
        check=True,
    )


if __name__ == "__main__":
    main(
