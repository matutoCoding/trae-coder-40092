from db.database import get_conn


def add_transaction(member_id, booking_id, tx_type, amount, description=""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO transactions (member_id, booking_id, type, amount, description)
            VALUES (?, ?, ?, ?, ?)
        """, (member_id, booking_id, tx_type, amount, description))


def get_transactions(member_id=None, limit=200):
    with get_conn() as conn:
        sql = """
            SELECT t.*, m.name as member_name
            FROM transactions t
            JOIN members m ON t.member_id = m.id
        """
        params = []
        if member_id:
            sql += " WHERE t.member_id=?"
            params.append(member_id)
        sql += " ORDER BY t.created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_equipment_list():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM equipment ORDER BY id"
        ).fetchall()]


def add_equipment(name, stock, price_per_hour):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO equipment (name, stock, price_per_hour) VALUES (?, ?, ?)
        """, (name, stock, price_per_hour))


def rent_equipment(member_id, equipment_id, quantity, hours, booking_id=None):
    with get_conn() as conn:
        eq = conn.execute(
            "SELECT * FROM equipment WHERE id=?", (equipment_id,)
        ).fetchone()
        if not eq:
            return False, "装备不存在"
        if eq['stock'] < quantity:
            return False, f"库存不足，仅剩 {eq['stock']} 件"

        amount = eq['price_per_hour'] * quantity * hours
        cur = conn.execute("""
            INSERT INTO equipment_rentals (booking_id, member_id, equipment_id,
                                           quantity, hours, amount, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (booking_id, member_id, equipment_id, quantity, hours, amount))
        rental_id = cur.lastrowid

        conn.execute("""
            UPDATE equipment SET stock = stock - ? WHERE id=?
        """, (quantity, equipment_id))

        if amount > 0:
            conn.execute("""
                INSERT INTO transactions (member_id, booking_id, type, amount, description)
                VALUES (?, ?, 'equipment', ?, ?)
            """, (member_id, booking_id, amount,
                  f"租赁{eq['name']} x{quantity} {hours}小时"))

    return True, rental_id


def return_equipment(rental_id):
    with get_conn() as conn:
        rental = conn.execute(
            "SELECT * FROM equipment_rentals WHERE id=?", (rental_id,)
        ).fetchone()
        if not rental or rental['status'] != 'active':
            return False, "租赁记录不存在或已归还"

        conn.execute("""
            UPDATE equipment_rentals SET status='returned' WHERE id=?
        """, (rental_id,))
        conn.execute("""
            UPDATE equipment SET stock = stock + ? WHERE id=?
        """, (rental['quantity'], rental['equipment_id']))

        return True, "归还成功"


def get_rentals(member_id=None, status=None):
    with get_conn() as conn:
        sql = """
            SELECT r.*, m.name as member_name, e.name as equipment_name
            FROM equipment_rentals r
            JOIN members m ON r.member_id = m.id
            JOIN equipment e ON r.equipment_id = e.id
        """
        conditions = []
        params = []
        if member_id:
            conditions.append("r.member_id=?")
            params.append(member_id)
        if status:
            conditions.append("r.status=?")
            params.append(status)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY r.created_at DESC LIMIT 200"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
