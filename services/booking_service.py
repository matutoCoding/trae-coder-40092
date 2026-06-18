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
    from services.quota_service import ensure_member_quota, use_quota_if_available
    from services.transaction_service import add_transaction

    if check_conflict(wall_id, date_str, start_time, end_time):
        return False, "该时段已被预约，请选择其他时段"

    quota_info = ensure_member_quota(member_id)
    use_quota, should_pay = use_quota_if_available(member_id)
    amount = 80.0 if should_pay else 0.0

    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO bookings (member_id, wall_id, slot_id, date, start_time, end_time,
                                  status, use_quota, is_paid, amount)
            VALUES (?, ?, 0, ?, ?, ?, 'booked', ?, ?, ?)
        """, (member_id, wall_id, date_str, start_time, end_time,
              1 if use_quota else 0, 1 if should_pay else 0, amount))
        booking_id = cur.lastrowid

        if use_quota:
            ym = datetime.now().strftime("%Y-%m")
            conn.execute("""
                UPDATE member_quotas SET used_quota = used_quota + 1
                WHERE member_id=? AND year_month=?
            """, (member_id, ym))

        if should_pay and amount > 0:
            add_transaction(member_id, booking_id, 'booking', amount,
                          f"{date_str} {start_time}-{end_time} 攀岩自费")

    return True, booking_id


def cancel_booking(booking_id):
    from services.quota_service import refund_quota
    from services.transaction_service import add_transaction

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
            refund_quota(booking['member_id'], booking['date'])

        if booking['amount'] > 0 and booking['is_paid'] == 1:
            add_transaction(booking['member_id'], booking_id, 'refund',
                          -booking['amount'], "取消预约退款")

        conn.execute("""
            UPDATE equipment_rentals SET status='returned'
            WHERE booking_id=? AND status='active'
        """, (booking_id,))

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
