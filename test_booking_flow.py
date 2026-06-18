import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db, seed_data
from services.quota_service import get_all_quotas, ensure_member_quota, reset_monthly_quotas
from services.booking_service import create_booking, cancel_booking, get_member_bookings, check_conflict
from services.transaction_service import get_transactions

def log(msg):
    print(f"[测试] {msg}")

def run_tests():
    init_db()
    seed_data()
    log("数据库初始化完成")

    quotas = get_all_quotas()
    log(f"加载所有会员额度: {len(quotas)} 条记录")
    for q in quotas:
        log(f"  - {q['member_name']}: {q['used_quota']}/{q['total_quota']}")

    member_id = 1
    wall_id = 1
    date_str = "2026-06-18"

    log(f"\n--- 测试1: 会员 {member_id} 预约第1次 (用免费额度) ---")
    ok, result = create_booking(member_id, wall_id, date_str, "09:00", "10:00")
    log(f"结果: ok={ok}, result={result}")
    assert ok, f"预约失败: {result}"

    quota = ensure_member_quota(member_id)
    log(f"当前额度: used={quota['used_quota']}/{quota['total_quota']}")
    assert quota['used_quota'] == 1, "额度应 +1"

    bookings = get_member_bookings(member_id)
    last = bookings[0]
    log(f"预约记录: amount={last['amount']}, use_quota={last['use_quota']}")
    assert last['amount'] == 0, "应为免费订单"
    assert last['use_quota'] == 1, "应使用额度"

    log(f"\n--- 测试2: 继续预约至额度用尽后，第5次应为自费 80 元 ---")
    times = [("10:00", "11:00"), ("11:00", "12:00"), ("12:00", "13:00"), ("13:00", "14:00")]
    for i, (st, et) in enumerate(times):
        ok, result = create_booking(member_id, wall_id, date_str, st, et)
        log(f"  第{i+2}次 {st}-{et}: ok={ok}")
        assert ok, f"预约失败: {result}"

    quota = ensure_member_quota(member_id)
    log(f"当前额度: used={quota['used_quota']}/{quota['total_quota']}")
    assert quota['used_quota'] == 4, f"额度应满4, 实际{quota['used_quota']}"

    log("--- 触发自费预约 (额度用尽) ---")
    ok, result = create_booking(member_id, wall_id, date_str, "14:00", "15:00")
    log(f"自费预约结果: ok={ok}, result={result}")
    assert ok, f"自费预约失败: {result}"

    bookings = get_member_bookings(member_id)
    paid = [b for b in bookings if b['amount'] > 0]
    log(f"自费订单数: {len(paid)}, 最近金额: ¥{paid[0]['amount']}")
    assert len(paid) >= 1, "应有至少1笔自费订单"
    assert paid[0]['amount'] == 80.0, "自费应为80元"

    txs = get_transactions(member_id)
    booking_txs = [t for t in txs if t['type'] == 'booking' and t['amount'] > 0]
    log(f"消费流水-预约收费: {len(booking_txs)} 笔, 金额: ¥{booking_txs[0]['amount'] if booking_txs else 0}")
    assert booking_txs, "应有收费流水记录"
    assert booking_txs[0]['amount'] == 80.0, "流水金额应为80"

    log(f"\n--- 测试3: 取消第一次预约后，同一时段可重新预约 ---")
    first_booking_id = None
    for b in get_member_bookings(member_id):
        if b['start_time'] == '09:00' and b['date'] == date_str:
            first_booking_id = b['id']
            break
    assert first_booking_id, "找不到09:00的预约"

    conflict_before = check_conflict(wall_id, date_str, "09:00", "10:00")
    log(f"取消前 09:00-10:00 冲突: {conflict_before}")
    assert conflict_before, "取消前应存在冲突"

    ok, msg = cancel_booking(first_booking_id)
    log(f"取消预约 {first_booking_id}: ok={ok}, {msg}")
    assert ok, "取消失败"

    quota_after_cancel = ensure_member_quota(member_id)
    log(f"取消后额度: used={quota_after_cancel['used_quota']}/{quota_after_cancel['total_quota']}")
    assert quota_after_cancel['used_quota'] == 3, f"额度应-1回到3, 实际{quota_after_cancel['used_quota']}"

    conflict_after = check_conflict(wall_id, date_str, "09:00", "10:00")
    log(f"取消后 09:00-10:00 冲突: {conflict_after}")
    assert not conflict_after, "取消后应无冲突"

    ok, result = create_booking(member_id, wall_id, date_str, "09:00", "10:00")
    log(f"重新预约同一时段 09:00-10:00: ok={ok}, result={result}")
    assert ok, f"取消后再约应成功: {result}"

    refund_txs = [t for t in get_transactions(member_id) if t['type'] == 'refund']
    log(f"退款流水: {len(refund_txs)} 笔")

    log(f"\n--- 测试4: 重置本月额度后清零 ---")
    reset_monthly_quotas()
    quota_reset = ensure_member_quota(member_id)
    log(f"重置后额度: used={quota_reset['used_quota']}/{quota_reset['total_quota']}")
    assert quota_reset['used_quota'] == 0, f"重置后used应=0, 实际{quota_reset['used_quota']}"

    log("\n" + "="*60)
    log("✅ 所有测试通过！")
    log("="*60)

if __name__ == "__main__":
    run_tests()
