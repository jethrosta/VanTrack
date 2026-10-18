"""SQLite persistence for campervan cleaning work logs."""
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "data" / "campervans.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS vehicles (
            fleet_number TEXT PRIMARY KEY,
            brand TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cleanings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fleet_number TEXT NOT NULL REFERENCES vehicles(fleet_number),
            cleaning_date TEXT NOT NULL,
            completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cleaners INTEGER NOT NULL CHECK(cleaners >= 1),
            total_fee_cents INTEGER NOT NULL CHECK(total_fee_cents >= 0),
            my_share_cents INTEGER NOT NULL CHECK(my_share_cents >= 0),
            paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0,1)),
            notes TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_cleaning_date ON cleanings(cleaning_date);
        """)


def upsert_vehicle(fleet_number, brand='', model='', notes=''):
    with connect() as con:
        con.execute("""
        INSERT INTO vehicles(fleet_number,brand,model,notes) VALUES(?,?,?,?)
        ON CONFLICT(fleet_number) DO UPDATE SET
            brand=CASE WHEN excluded.brand != '' THEN excluded.brand ELSE vehicles.brand END,
            model=CASE WHEN excluded.model != '' THEN excluded.model ELSE vehicles.model END
        """, (fleet_number, brand.strip(), model.strip(), notes.strip()))


def save_cleaning(fleet_number, cleaning_date, cleaners, fee_cents, notes=''):
    # Exact money is stored as integer cents; the app rounds half-up for fractional cents.
    from decimal import Decimal, ROUND_HALF_UP
    my_share_cents = int((Decimal(fee_cents) / Decimal(cleaners)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    with connect() as con:
        cur = con.execute("""
            INSERT INTO cleanings(fleet_number,cleaning_date,cleaners,total_fee_cents,my_share_cents,notes)
            VALUES(?,?,?,?,?,?)
        """, (fleet_number, cleaning_date, cleaners, fee_cents, my_share_cents, notes.strip()))
        return cur.lastrowid


def read_cleanings():
    with connect() as con:
        return pd.read_sql_query("""
            SELECT c.id, c.cleaning_date, c.fleet_number, v.brand, v.model,
                   c.cleaners, c.total_fee_cents, c.my_share_cents,
                   c.paid, c.notes, c.completed_at
            FROM cleanings c JOIN vehicles v USING(fleet_number)
            ORDER BY c.cleaning_date DESC, c.id DESC
        """, con)


def read_vehicles():
    with connect() as con:
        return pd.read_sql_query("""
            SELECT v.fleet_number, v.brand, v.model, v.notes, v.created_at,
                COUNT(c.id) AS times_cleaned,
                COALESCE(SUM(c.my_share_cents), 0) AS total_earned_cents
            FROM vehicles v LEFT JOIN cleanings c USING(fleet_number)
            GROUP BY v.fleet_number ORDER BY v.fleet_number
        """, con)


def set_paid(job_id, paid):
    with connect() as con:
        con.execute("UPDATE cleanings SET paid=? WHERE id=?", (int(paid), int(job_id)))


def delete_cleaning(job_id):
    with connect() as con:
        con.execute("DELETE FROM cleanings WHERE id=?", (int(job_id),))
