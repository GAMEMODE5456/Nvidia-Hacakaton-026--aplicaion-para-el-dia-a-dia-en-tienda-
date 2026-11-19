import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "miscelanea.db")


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS productos(
            id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL,
            cantidad REAL NOT NULL DEFAULT 0, precio REAL);
        CREATE TABLE IF NOT EXISTS movimientos(
            id INTEGER PRIMARY KEY, lote INTEGER, producto TEXT NOT NULL,
            delta REAL NOT NULL, motivo TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP,
            deshecho INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS alias(
            alias TEXT PRIMARY KEY, nombre TEXT NOT NULL);
        """)
