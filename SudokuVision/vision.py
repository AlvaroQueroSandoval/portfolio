"""Detección de cuadrícula y lectura asistida de dígitos impresos.

El reconocimiento nunca resuelve ni modifica pistas para forzar una solución.
"""
import base64
from io import BytesIO
from pathlib import Path
from threading import Lock
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "2")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from solver import conflicts

MODEL_PATH = Path(__file__).resolve().parent / "models" / "sudoku_digit_model.h5"
_model = None
_lock = Lock()
MAX_PIXELS = 12_000_000


class ImageError(ValueError):
    pass


def decode_image(blob):
    try:
        with Image.open(BytesIO(blob)) as source:
            if source.format not in {"PNG", "JPEG"}:
                raise ImageError("Usa una imagen PNG o JPG.")
            if source.width * source.height > MAX_PIXELS:
                raise ImageError("La imagen supera los 12 megapíxeles. Reduce su tamaño.")
            if min(source.size) < 250:
                raise ImageError("La imagen es demasiado pequeña. Usa al menos 250 píxeles por lado.")
            source.load()
            rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("No se puede abrir el archivo como imagen PNG o JPG.") from exc
    image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ratio = min(1.0, 1600 / max(image.shape[:2]))
    if ratio < 1:
        image = cv2.resize(image, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
    return image


def ordered_corners(points):
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    center = points.mean(axis=0)
    ordered = points[np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))]
    ordered = np.roll(ordered, -np.argmin(ordered.sum(axis=1)), axis=0)
    if len(np.unique(ordered, axis=0)) != 4:
        raise ImageError("El contorno del tablero no es válido.")
    return ordered


def warp_board(image, points):
    pts = ordered_corners(points)
    lengths = [np.linalg.norm(pts[i] - pts[(i + 1) % 4]) for i in range(4)]
    if min(lengths) < 230:
        raise ImageError("El tablero ocupa muy pocos píxeles. Acerca la cámara o recorta la imagen.")
    destination = np.float32([[0, 0], [539, 0], [539, 539], [0, 539]])
    return cv2.warpPerspective(image, cv2.getPerspectiveTransform(pts, destination), (540, 540))


def normalize(gray):
    background = cv2.GaussianBlur(gray, (0, 0), 15)
    return cv2.divide(gray, np.maximum(background, 1), scale=255)


def grid_score(warped):
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(normalize(gray), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 31, 9)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((1, 35), np.uint8))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((35, 1), np.uint8))
    def lines(mask, axis):
        strength = np.mean(mask > 0, axis=axis)
        return sum(float(strength[max(0, i * 60 - 8):min(540, i * 60 + 9)].max()) > .42
                   for i in range(1, 9))
    return lines(horizontal, 1), lines(vertical, 0)


def detect_board(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 31, 9)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:30]:
        if cv2.contourArea(contour) < gray.size * .12:
            continue
        poly = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
        if len(poly) == 4 and cv2.isContourConvex(poly):
            try:
                warped = warp_board(image, poly)
                score = grid_score(warped)
                if min(score) >= 7:
                    candidates.append((sum(score), cv2.contourArea(contour), warped))
            except ImageError:
                continue
    if not candidates:
        raise ImageError("No se reconoce una cuadrícula 9 × 9 suficientemente clara. Incluye el tablero completo, con buena luz.")
    return max(candidates, key=lambda c: (c[0], c[1]))[2]


def digit_tensor(cell):
    corrected = normalize(cell)
    # Un umbral absoluto evita amplificar el ruido de una casilla vacía.
    corrected = cv2.GaussianBlur(corrected, (3, 3), .6)
    threshold, _ = cv2.threshold(corrected, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, binary = cv2.threshold(corrected, min(threshold, 195), 255, cv2.THRESH_BINARY_INV)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(binary)
    candidates = []
    h, w = cell.shape
    for label in range(1, count):
        x, y, bw, bh, area = stats[label]
        cx, cy = centers[label]
        if area >= 8 and bh >= h * .22 and bw < w * .95 and bh < h * .98:
            if .12 * w < cx < .88 * w and .1 * h < cy < .9 * h:
                candidates.append((int(area), label))
    if not candidates:
        return None
    _, label = max(candidates)
    x, y, bw, bh, _ = stats[label]
    digit = np.uint8(labels[y:y + bh, x:x + bw] == label) * 255
    scale = 20 / max(bw, bh)
    nw, nh = max(1, round(bw * scale)), max(1, round(bh * scale))
    digit = cv2.resize(digit, (nw, nh), interpolation=cv2.INTER_AREA)
    # Segunda escala suave: conserva trazos finos sin engrosarlos por dilatación.
    yy, xx = np.where(digit > 25)
    if not len(yy):
        return None
    digit = digit[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
    scale = 18 / max(digit.shape)
    nh, nw = [max(1, round(length * scale)) for length in digit.shape]
    digit = cv2.resize(digit, (nw, nh), interpolation=cv2.INTER_LINEAR)
    mask = np.zeros((28, 28), np.float32)
    mask[(28 - nh) // 2:(28 - nh) // 2 + nh, (28 - nw) // 2:(28 - nw) // 2 + nw] = digit / 255
    return mask[..., None]


def get_model():
    global _model
    if _model is None:
        from tensorflow.keras.models import load_model
        _model = load_model(MODEL_PATH, compile=False)
    return _model


def read_image(blob):
    warped = detect_board(decode_image(blob))
    sharpness = cv2.Laplacian(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    if sharpness < 35:
        raise ImageError("La imagen está demasiado desenfocada. Prueba una foto más nítida o introduce las pistas a mano.")
    tasks, positions = [], []
    for turns in range(4):
        rotated = np.rot90(warped, turns).copy()
        gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        for r in range(9):
            for c in range(9):
                tensor = digit_tensor(gray[r * 60 + 6:(r + 1) * 60 - 6, c * 60 + 6:(c + 1) * 60 - 6])
                if tensor is not None:
                    tasks.append(tensor)
                    positions.append((turns, r, c))
    if not tasks:
        raise ImageError("La cuadrícula no contiene cifras legibles. Prueba otra imagen o introduce las pistas a mano.")
    with _lock:
        predictions = np.asarray(get_model()(np.stack(tasks), training=False))
    boards = [[[0 for _ in range(9)] for _ in range(9)] for _ in range(4)]
    confidence = [[[None for _ in range(9)] for _ in range(9)] for _ in range(4)]
    doubtful = [[] for _ in range(4)]
    for (turns, r, c), pred in zip(positions, predictions):
        digit = int(np.argmax(pred))
        certainty = float(pred[digit])
        confidence[turns][r][c] = round(certainty, 4)
        # La marca de duda se conserva incluso si el modelo propone 0.
        boards[turns][r][c] = digit
        if digit == 0 or certainty < .95:
            doubtful[turns].append([r, c])
    def quality(turns):
        values = [v for row in confidence[turns] for v in row if v is not None]
        return np.mean(values) - .05 * len(conflicts(boards[turns])) - .025 * len(doubtful[turns])
    best = max(range(4), key=quality)
    board = boards[best]
    if sum(n != 0 for row in board for n in row) < 8:
        raise ImageError("Se han leído muy pocas pistas con claridad. Usa otra imagen o el modo manual.")
    bad = conflicts(board)
    preview = np.rot90(warped, best).copy()
    _, jpeg = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return {"board": board, "uncertain": doubtful[best], "conflicts": bad,
            "confidence": confidence[best], "rotation": best * 90,
            "preview": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii"),
            "message": "Comprueba todas las pistas con la imagen antes de resolver. Puedes editar cualquier casilla."}
