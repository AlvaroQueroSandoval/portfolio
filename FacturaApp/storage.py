"""Historial y PDF en una misma transacción. Las tarifas no alteran el pasado."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from core import calculate, validate_details


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS catalog (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_key TEXT UNIQUE NOT NULL, number TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL, body TEXT NOT NULL, pdf BLOB NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def catalog(self):
        with self.connect() as db:
            return {row["id"]: json.loads(row["body"]) for row in db.execute("SELECT * FROM catalog")}

    def update_catalog(self, products, errors):
        with self.connect() as db:
            for key, product in products.items():
                db.execute("INSERT OR REPLACE INTO catalog VALUES (?,?)", (key, json.dumps(product, ensure_ascii=False)))
            for key, value in {
                "last_attempt": datetime.now(timezone.utc).isoformat(),
                "refresh_errors": json.dumps(errors, ensure_ascii=False),
            }.items():
                db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, value))

    def metadata(self):
        with self.connect() as db:
            return dict(db.execute("SELECT key,value FROM metadata").fetchall())

    def save_document(self, details, items, catalog, request_key, renderer):
        details = validate_details(details)
        totals = calculate(items, catalog)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM documents WHERE request_key=?", (request_key,)).fetchone()
            if existing:
                return dict(existing)
            seq = db.execute("SELECT COALESCE(MAX(id),0)+1 FROM documents").fetchone()[0]
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            prefix = "PRE" if details["kind"] == "Presupuesto de materiales" else "DEMO"
            number = f"{prefix}-{now[:4]}-{seq:06d}"
            document = dict(details, **totals, number=number, created_at=now)
            pdf = renderer(document)  # Si falla, se revierte toda la operación.
            db.execute("INSERT INTO documents(request_key,number,created_at,body,pdf) VALUES (?,?,?,?,?)",
                       (request_key, number, now, json.dumps(document, ensure_ascii=False), pdf))
            return dict(db.execute("SELECT * FROM documents WHERE request_key=?", (request_key,)).fetchone())

    def history(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,number,created_at,body FROM documents ORDER BY id DESC")]

    def pdf(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT pdf FROM documents WHERE id=?", (identifier,)).fetchone()
            return bytes(row["pdf"]) if row else None
