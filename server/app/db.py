import hashlib
import sqlite3
from pathlib import Path

# Base de datos SQLite en un archivo (no en memoria): persiste entre
# reinicios del servidor, como pasaria en una app real. Usuarios y catalogo
# son ficticios.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tienda.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance INTEGER NOT NULL,
            is_vip INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS productos (
            producto TEXT PRIMARY KEY,
            precio INTEGER NOT NULL
        );
        """
    )
    conn.executemany(
        "INSERT OR IGNORE INTO users (id, username, password_hash, balance, is_vip) VALUES (?, ?, ?, ?, ?)",
        [
            # Hash simple (sha256 sin sal) solo para esta demo: el foco del
            # desafio es el JWT, no el almacenamiento de contraseñas.
            (1, "alice", hashlib.sha256(b"alice123").hexdigest(), 100, 0),
            (2, "bob", hashlib.sha256(b"bob123").hexdigest(), 5000, 1),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO productos (producto, precio) VALUES (?, ?)",
        [
            ("mouse", 80),
            ("teclado", 150),
            ("monitor-4k", 4500),
            ("notebook-gamer", 9999),
        ],
    )
    conn.commit()
    conn.close()


def _row_to_user(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "password_hash": row["password_hash"],
        "balance": row["balance"],
        "is_vip": bool(row["is_vip"]),
    }


def find_user(username):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def check_password(username, password):
    user = find_user(username)
    if not user:
        return None
    if user["password_hash"] != hashlib.sha256(password.encode()).hexdigest():
        return None
    return user


def catalogo():
    conn = _connect()
    rows = conn.execute("SELECT producto, precio FROM productos ORDER BY precio").fetchall()
    conn.close()
    return [{"producto": r["producto"], "precio": r["precio"]} for r in rows]


def producto_por_nombre(nombre):
    conn = _connect()
    row = conn.execute("SELECT producto, precio FROM productos WHERE producto = ?", (nombre,)).fetchone()
    conn.close()
    return {"producto": row["producto"], "precio": row["precio"]} if row else None
