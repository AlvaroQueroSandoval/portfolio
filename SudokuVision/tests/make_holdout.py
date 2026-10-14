"""Conjunto adicional: cinco tableros y cinco fuentes no usadas en el ajuste.

Las imágenes ya están incluidas. Para regenerarlas se necesitan las fuentes
de Windows indicadas; no se distribuyen los archivos de fuentes.
"""
import json
from pathlib import Path
import cv2
import numpy as np
from make_fixtures import generate, render, ROOT


if __name__ == "__main__":
    folder = ROOT / "tests/fixtures"
    manifest = []
    for i, font in enumerate(["times.ttf", "verdana.ttf", "calibri.ttf", "tahoma.ttf", "cour.ttf"], 6):
        font_path = Path("C:/Windows/Fonts") / font
        if not font_path.exists():
            raise FileNotFoundError(f"Fuente necesaria para regenerar este conjunto: {font_path}")
        board, solution = generate(1000*i + 43)
        image = render(board, font_path=font_path)
        versions = {
            "normal": image,
            "giro_90": cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
            "sombra": (image.astype(float)*np.linspace(.35, 1, 760)[None, :, None]).astype(np.uint8),
            "reducido_300": cv2.resize(image, (300, 300), interpolation=cv2.INTER_AREA),
        }
        record = {"id": i, "seed": 1000*i+43, "font": font, "board": board,
                  "solution": solution, "images": {}}
        for name, img in versions.items():
            filename = f"holdout-{i}-{name}.png"
            cv2.imwrite(str(folder/filename), img)
            record["images"][name] = filename
        manifest.append(record)
    (folder/"holdout.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
