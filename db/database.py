import sqlite3
import os
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'climbing.db')


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS walls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            difficulty TEXT NOT NULL,
            description TEXT,
            status INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wall_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            capacity INTEGER DEFAULT 1,
            FOREIGN KEY (wall_id) REFERENCES walls(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            member_type TEXT DEFAULT 'normal',
            monthly_quota INTEGER DEFAULT 4,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS member_quotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            year_month TEXT NOT NULL,
            total_quota INTEGER NOT NULL,
            used_quota INTEGER DEFAULT 0,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            UNIQUE(member_id, year_month)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            wall_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT DEFAULT 'booked',
            use_quota INTEGER DEFAULT 1,
            is_paid INTEGER DEFAULT 0,
            amount REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (wall_id) REFERENCES walls(id),
            FOREIGN KEY (slot_id) REFERENCES time_slots(id)
        );

        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            price_per_hour REAL DEFAULT 0,
            status INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS equipment_rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            member_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            hours INTEGER DEFAULT 1,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(id),
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            booking_id INTEGER,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        );
        """)


def seed_data():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM walls")
        if c.fetchone()[0] == 0:
            walls = [
                ('初学者道A', '初级', '适合新手练习的平缓岩壁'),
                ('进阶道B', '中级', '有一定难度的进阶岩壁'),
                ('高级道C', '高级', '高难度专业岩壁'),
                ('抱石区D', '中级', '抱石练习区'),
                ('速度道E', '初级', '速度训练专用道')
            ]
            c.executemany(
                "INSERT INTO walls (name, difficulty, description) VALUES (?, ?, ?)",
                walls
            )
        c.execute("SELECT COUNT(*) FROM equipment")
        if c.fetchone()[0] == 0:
            equipment = [
                ('攀岩鞋', 20, 10.0),
                ('安全绳', 15, 5.0),
                ('安全带', 25, 8.0),
                ('头盔', 30, 6.0),
                ('镁粉袋', 50, 3.0)
            ]
            c.executemany(
                "INSERT INTO equipment (name, stock, price_per_hour) VALUES (?, ?, ?)",
                equipment
            )
        c.execute("SELECT COUNT(*) FROM members")
        if c.fetchone()[0] == 0:
            members = [
                ('张三', '13800138001', 'normal', 4),
                ('李四', '13800138002', 'vip', 8),
                ('王五', '13800138003', 'normal', 4)
            ]
            c.executemany(
                "INSERT INTO members (name, phone, member_type, monthly_quota) VALUES (?, ?, ?, ?)",
                members
            )
