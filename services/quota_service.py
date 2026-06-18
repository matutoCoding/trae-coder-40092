from db.database import get_conn
from datetime import datetime


def get_current_ym():
    return datetime.now().strftime("%Y-%m")


def ensure_member_quota(member_id):
    ym = get_current_ym()
    with get_conn() as conn:
        member = conn.execute(
            "SELECT monthly_quota FROM members WHERE id=?", (member_id,)
        ).fetchone()
        if not member:
            return None
        monthly_quota = member['monthly_quota']
        existing = conn.execute("""
            SELECT * FROM member_quotas WHERE member_id=? AND year_month=?
        """, (member_id, ym)).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO member_quotas (member_id, year_month, total_quota, used_quota)
                VALUES (?, ?, ?, 0)
            """, (member_id, ym, monthly_quota))
            existing = conn.execute("""
                SELECT * FROM member_quotas WHERE member_id=? AND year_month=?
            """, (member_id, ym)).fetchone()
        return dict(existing)


def use_quota_if_available(member_id):
    quota_info = ensure_member_quota(member_id)
    if not quota_info:
        return False, True
    remaining = quota_info['total_quota'] - quota_info['used_quota']
    if remaining > 0:
        return True, False
    return False, True


def refund_quota(member_id, date_str):
    try:
        ym = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
    except Exception:
        ym = get_current_ym()
    with get_conn() as conn:
        conn.execute("""
            UPDATE member_quotas SET used_quota = MAX(0, used_quota - 1)
            WHERE member_id=? AND year_month=?
        """, (member_id, ym))


def reset_monthly_quotas(ym=None):
    if ym is None:
        ym = get_current_ym()
    with get_conn() as conn:
        members = conn.execute("SELECT id, monthly_quota FROM members").fetchall()
        for m in members:
            existing = conn.execute("""
                SELECT id FROM member_quotas WHERE member_id=? AND year_month=?
            """, (m['id'], ym)).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO member_quotas (member_id, year_month, total_quota, used_quota)
                    VALUES (?, ?, ?, 0)
                """, (m['id'], ym, m['monthly_quota']))


def get_all_quotas(ym=None):
    if ym is None:
        ym = get_current_ym()
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT q.*, m.name as member_name, m.phone, m.member_type
            FROM member_quotas q
            JOIN members m ON q.member_id = m.id
            WHERE q.year_month=?
            ORDER BY m.name
        """, (ym,)).fetchall()]


def get_all_members():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM members ORDER BY name"
        ).fetchall()]


def add_member(name, phone, member_type='normal', monthly_quota=4):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO members (name, phone, member_type, monthly_quota)
            VALUES (?, ?, ?, ?)
        """, (name, phone, member_type, monthly_quota))


def update_member(member_id, name, phone, member_type, monthly_quota):
    with get_conn() as conn:
        conn.execute("""
            UPDATE members SET name=?, phone=?, member_type=?, monthly_quota=?
            WHERE id=?
        """, (name, phone, member_type, monthly_quota, member_id))
