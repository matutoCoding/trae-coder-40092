from db.database import get_conn


def get_all_walls():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM walls ORDER BY id"
        ).fetchall()]


def add_wall(name, difficulty, description=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO walls (name, difficulty, description) VALUES (?, ?, ?)",
            (name, difficulty, description)
        )


def update_wall(wall_id, name, difficulty, description):
    with get_conn() as conn:
        conn.execute(
            "UPDATE walls SET name=?, difficulty=?, description=? WHERE id=?",
            (name, difficulty, description, wall_id)
        )


def delete_wall(wall_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM walls WHERE id=?", (wall_id,))


def get_available_slots(wall_id, date_str):
    with get_conn() as conn:
        booked = conn.execute("""
            SELECT start_time, end_time FROM bookings
            WHERE wall_id=? AND date=? AND status='booked'
        """, (wall_id, date_str)).fetchall()
        all_slots = _generate_default_slots()
        available = []
        for s in all_slots:
            conflict = False
            for b in booked:
                if _is_overlap(s['start'], s['end'], b['start_time'], b['end_time']):
                    conflict = True
                    break
            if not conflict:
                available.append(s)
        return available


def _generate_default_slots():
    slots = []
    for hour in range(9, 21):
        slots.append({
            'start': f"{hour:02d}:00",
            'end': f"{hour+1:02d}:00"
        })
    return slots


def _is_overlap(s1, e1, s2, e2):
    from datetime import datetime
    fmt = "%H:%M"
    t1s = datetime.strptime(s1, fmt)
    t1e = datetime.strptime(e1, fmt)
    t2s = datetime.strptime(s2, fmt)
    t2e = datetime.strptime(e2, fmt)
    return t1s < t2e and t2s < t1e


def get_booked_slots(wall_id, date_str):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT b.*, m.name as member_name FROM bookings b
            JOIN members m ON b.member_id = m.id
            WHERE b.wall_id=? AND b.date=? AND b.status='booked'
            ORDER BY b.start_time
        """, (wall_id, date_str)).fetchall()]
