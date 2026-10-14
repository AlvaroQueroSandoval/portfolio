"""Aplicación Flask: imágenes en memoria, sin galería pública de subidas."""
from collections import OrderedDict
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import monotonic
import os
from io import BytesIO

from flask import Flask, Request, jsonify, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from solver import solve_board
from vision import read_image, ImageError

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)


class MemoryRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return BytesIO()


app.request_class = MemoryRequest
app.config.update(MAX_CONTENT_LENGTH=8 * 1024 * 1024)
slots = BoundedSemaphore(2)
rate_lock = Lock()
visits = OrderedDict()


def error(message, status):
    return jsonify(message=message, status="error"), status


@app.after_request
def headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'self'"
    )
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.before_request
def protect_api():
    if request.path.startswith("/api/") and request.method == "POST":
        if request.headers.get("X-Sudoku-Request") != "1":
            return error("Abre la aplicación para realizar esta operación.", 403)
        if app.config.get("TESTING"):
            return None
        now = monotonic()
        key = request.remote_addr or "unknown"
        with rate_lock:
            recent = [t for t in visits.pop(key, []) if now - t < 60]
            if len(recent) >= 20:
                visits[key] = recent
                return error("Has hecho muchas peticiones. Espera un minuto e inténtalo de nuevo.", 429)
            visits[key] = recent + [now]
            while len(visits) > 2048:
                visits.popitem(last=False)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exc):
    return error("El archivo supera los 8 MB. Reduce el tamaño de la imagen.", 413)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/api/read")
def recognize():
    if not slots.acquire(blocking=False):
        return error("La aplicación está procesando otras imágenes. Inténtalo en unos segundos.", 503)
    try:
        upload = request.files.get("image")
        if not upload or not upload.filename:
            return error("Selecciona una imagen PNG o JPG.", 400)
        return jsonify(read_image(upload.read()))
    except ImageError as exc:
        return error(str(exc), 422)
    except HTTPException:
        raise
    except Exception:
        app.logger.exception("Fallo interno de reconocimiento")
        return error("No se ha podido analizar esta imagen. Puedes introducir el tablero manualmente.", 500)
    finally:
        slots.release()


@app.post("/api/solve")
def solve():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error("Envía un tablero válido para resolver.", 400)
    if not slots.acquire(blocking=False):
        return error("La aplicación está ocupada. Inténtalo en unos segundos.", 503)
    try:
        return jsonify(solve_board(payload.get("board")))
    except ValueError as exc:
        return error(str(exc), 400)
    finally:
        slots.release()


if __name__ == "__main__":
    from waitress import serve
    serve(app, host=os.environ.get("HOST", "127.0.0.1"),
          port=int(os.environ.get("PORT", "8000")), threads=4,
          max_request_body_size=8 * 1024 * 1024, inbuf_overflow=8 * 1024 * 1024)
