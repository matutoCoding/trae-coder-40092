from db.database import get_conn
from datetime import datetime


def check_conflict(wall_id, date_str, start_time, end_time, exclude_booking_id=None):
    with get_conn() as conn:
        sql = """
            SELECT COUNT(*) FROM bookings
            WHERE wall_id=? AND date=? AND status='booked'
            AND (
                (start_time < ? AND end_time > ?)
                OR (start_time < ? AND end_time > ?)
                OR (start_time >= ? AND end_time <= ?)
            )
        """
        params = [wall_id, date_str, end_time, start_time, end_time, start_time, start_time, end_time]
        if exclude_booking_id:
            sql += " AND id != ?"
            params.append(exclude_booking_id)
        count = conn.execute(sql, params).fetchone()[0]
        return count > 0


def create_booking(member_id, wall_id, date_str, start_time, end_time):
    from services.quota_service import _ensure_quota_with_conn

    if check_conflict(wall_id, date_str, start_time, end_time):
        return False, "该时段已被预约，请选择其他时段"

    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d")
        ym = booking_date.strftime("%Y-%m")
    except Exception:
        ym = datetime.now().strftime("%Y-%m")

    with get_conn() as conn:
        _ensure_quota_with_conn(conn, member_id, ym)

        quota_info = conn.execute("""
            SELECT total_quota, used_quota FROM member_quotas
            WHERE member_id=? AND year_month=?
        """, (member_id, ym)).fetchone()

        remaining = quota_info['total_quota'] - quota_info['used_quota']
        use_quota = remaining > 0
        should_pay = not use_quota
        amount = 80.0 if should_pay else 0.0

        cur = conn.execute("""
            INSERT INTO bookings (member_id, wall_id, slot_id, date, start_time, end_time,
                                  status, use_quota, is_paid, amount)
            VALUES (?, ?, NULL, ?, ?, ?, 'booked', ?, ?, ?)
        """, (member_id, wall_id, date_str, start_time, end_time,
              1 if use_quota else 0, 1 if should_pay else 0, amount))
        booking_id = cur.lastrowid

        if use_quota:
            conn.execute("""
                UPDATE member_quotas SET used_quota = used_quota + 1
                WHERE member_id=? AND year_month=?
            """, (member_id, ym))

        if should_pay and amount > 0:
            conn.execute("""
                INSERT INTO transactions (member_id, booking_id, type, amount, description)
                VALUES (?, ?, 'booking', ?, ?)
            """, (member_id, booking_id, amount,
                  f"{date_str} {start_time}-{end_time} 攀岩自费"))

    return True, booking_id


def cancel_booking(booking_id):
    with get_conn() as conn:
        booking = conn.execute(
            "SELECT * FROM bookings WHERE id=?", (booking_id,)
        ).fetchone()
        if not booking or booking['status'] != 'booked':
            return False, "预约不存在或已取消"

        conn.execute(
            "UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,)
        )

        if booking['use_quota'] == 1:
            try:
                ym = datetime.strptime(booking['date'], "%Y-%m-%d").strftime("%Y-%m")
            except Exception:
                ym = datetime.now().strftime("%Y-%m")
            conn.execute("""
                UPDATE member_quotas SET used_quota = MAX(0, used_quota - 1)
                WHERE member_id=? AND year_month=?
            """, (booking['member_id'], ym))

        if booking['amount'] > 0 and booking['is_paid'] == 1:
            conn.execute("""
                INSERT INTO transactions (member_id, booking_id, type, amount, description)
                VALUES (?, ?, 'refund', ?, ?)
            """, (booking['member_id'], booking_id, -booking['amount'], "取消预约退款"))

        rentals = conn.execute("""
            SELECT id, equipment_id, quantity FROM equipment_rentals
            WHERE booking_id=? AND status='active'
        """, (booking_id,)).fetchall()
        for r in rentals:
            conn.execute("""
                UPDATE equipment_rentals SET status='returned' WHERE id=?
            """, (r['id'],))
            conn.execute("""
                UPDATE equipment SET stock = stock + ? WHERE id=?
            """, (r['quantity'], r['equipment_id']))

    return True, "取消成功，时段已释放"


def get_member_bookings(member_id=None):
    with get_conn() as conn:
        sql = """
            SELECT b.*, m.name as member_name, w.name as wall_name
            FROM bookings b
            JOIN members m ON b.member_id = m.id
            JOIN walls w ON b.wall_id = w.id
        """
        if member_id:
            sql += " WHERE b.member_id=?"
            rows = conn.execute(sql, (member_id,)).fetchall()
        else:
            sql += " ORDER BY b.created_at DESC LIMIT 200"
            rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
