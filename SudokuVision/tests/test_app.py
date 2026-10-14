import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app, visits, slots
from solver import conflicts, solve_board
from vision import decode_image, ImageError

PUZZLES = json.loads((ROOT / "tests/fixtures/manifest.json").read_text())
HEADERS = {"X-Sudoku-Request": "1"}


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    app.config["TESTING"] = False


@pytest.mark.parametrize("puzzle", PUZZLES)
def test_unique_solution_preserves_clues(puzzle):
    before = [row[:] for row in puzzle["board"]]
    result = solve_board(puzzle["board"])
    assert result["status"] == "solved"
    assert result["solution"] == puzzle["solution"]
    assert puzzle["board"] == before
    assert not conflicts(result["solution"])
    for row in result["solution"]:
        assert set(row) == set(range(1, 10))


@pytest.mark.parametrize("value", [None, [], [[0]*9]*8, [[0]*8]*9,
    [[True]*9]*9, [[1.5]*9]*9, [["1"]*9]*9, [[10]*9]*9, [[-1]*9]*9])
def test_malformed_board(value):
    with pytest.raises(ValueError):
        solve_board(value)


def test_invalid_full_board_is_not_solved():
    result = solve_board([[1]*9 for _ in range(9)])
    assert result["status"] == "conflict"
    assert "solution" not in result


def test_empty_multiple_and_limit_are_not_solutions():
    empty = [[0]*9 for _ in range(9)]
    assert solve_board(empty)["status"] == "insufficient"
    empty[0][0] = 1
    result = solve_board(empty)
    assert result["status"] == "multiple" and "solution" not in result
    result = solve_board(PUZZLES[0]["board"], max_nodes=0)
    assert result["status"] == "limit" and "solution" not in result


def test_unsolvable_without_duplicate():
    b = [row[:] for row in PUZZLES[0]["board"]]
    # Una pista incorrecta, sin duplicados inmediatos, que contradice la solución.
    b[0][0] = 6
    assert not conflicts(b)
    result = solve_board(b)
    assert result["status"] == "unsolvable"
    assert "solution" not in result


def test_api_requires_valid_payload(client):
    assert client.post("/api/solve", json={}).status_code == 403
    for data in [{}, {"confirmed": False}, {"confirmed": True, "board": "bad"}]:
        assert client.post("/api/solve", json=data, headers=HEADERS).status_code == 400
    result = client.post("/api/solve", json={"board": PUZZLES[0]["board"]}, headers=HEADERS)
    assert result.json["solution"] == PUZZLES[0]["solution"]


def png(image):
    return cv2.imencode(".png", image)[1].tobytes()


@pytest.mark.parametrize("kind", ["invalid", "white", "rectangle", "empty_grid", "tiny"])
def test_rejects_non_sudoku(client, kind):
    image = np.full((600, 600, 3), 255, np.uint8)
    if kind == "rectangle":
        cv2.rectangle(image, (20, 20), (580, 580), (0, 0, 0), 4)
    if kind == "empty_grid":
        for i in range(10):
            p = 30 + i*60
            cv2.line(image, (30, p), (570, p), (0, 0, 0), 3)
            cv2.line(image, (p, 30), (p, 570), (0, 0, 0), 3)
    blob = b"not an image" if kind == "invalid" else png(image[:144, :144] if kind == "tiny" else image)
    response = client.post("/api/read", data={"image": (io.BytesIO(blob), "board.png")}, headers=HEADERS)
    assert response.status_code == 422
    assert "board" not in response.json


def test_upload_limits_and_missing_file(client):
    assert client.post("/api/read", headers=HEADERS).status_code == 400
    result = client.post("/api/read", data={"image": (io.BytesIO(b"x"*(8*1024*1024)), "large.png")}, headers=HEADERS)
    assert result.status_code == 413
    with pytest.raises(ImageError, match="megap"):
        decode_image(png(np.zeros((3500, 3500, 3), np.uint8)))


def test_busy_and_rate_limit(client):
    slots.acquire()
    slots.acquire()
    try:
        assert client.post("/api/read", headers=HEADERS).status_code == 503
    finally:
        slots.release()
        slots.release()
    visits.clear()
    app.config["TESTING"] = False
    for _ in range(20):
        assert client.post("/api/read", headers=HEADERS).status_code == 400
    assert client.post("/api/read", headers=HEADERS).status_code == 429
    visits.clear()


def test_page_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'id="board"' in response.data
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert client.get("/health").json == {"status": "ok"}
