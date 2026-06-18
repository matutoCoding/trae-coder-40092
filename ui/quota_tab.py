from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QHeaderView,
                             QLabel, QGroupBox, QSpinBox)
from PyQt6.QtGui import QColor, QBrush
from services.quota_service import (get_all_quotas, get_all_members, add_member,
                                     update_member, reset_monthly_quotas, get_current_ym,
                                     ensure_member_quota)
from services.booking_service import get_member_bookings


class QuotaTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_members()
        self.load_quotas()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        self.ym_label = QLabel(f"当前月份：{get_current_ym()}")
        top_bar.addWidget(self.ym_label)
        top_bar.addStretch()

        self.btn_reset = QPushButton("重置本月额度")
        self.btn_reset.clicked.connect(self.reset_quotas)
        top_bar.addWidget(self.btn_reset)

        self.btn_add_member = QPushButton("新增会员")
        self.btn_add_member.clicked.connect(self.add_member_dialog)
        top_bar.addWidget(self.btn_add_member)

        self.btn_edit_member = QPushButton("编辑会员")
        self.btn_edit_member.clicked.connect(self.edit_member_dialog)
        top_bar.addWidget(self.btn_edit_member)

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.load_quotas)
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        main_layout = QHBoxLayout()

        left_group = QGroupBox("会员月度额度")
        left_layout = QVBoxLayout()
        self.quota_table = QTableWidget()
        self.quota_table.setColumnCount(7)
        self.quota_table.setHorizontalHeaderLabels(
            ["会员ID", "姓名", "手机号", "类型", "总额度", "已使用", "剩余"]
        )
        self.quota_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.quota_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.quota_table)
        left_group.setLayout(left_layout)
        main_layout.addWidget(left_group, 2)

        right_group = QGroupBox("会员预约记录")
        right_layout = QVBoxLayout()
        self.booking_table = QTableWidget()
        self.booking_table.setColumnCount(6)
        self.booking_table.setHorizontalHeaderLabels(
            ["日期", "时段", "岩壁道", "状态", "是否额度", "金额"]
        )
        self.booking_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.booking_table)

        self.quota_table.itemSelectionChanged.connect(self.on_member_selected)
        right_group.setLayout(right_layout)
        main_layout.addWidget(right_group, 2)

        layout.addLayout(main_layout)

    def load_members(self):
        self.members = get_all_members()

    def load_quotas(self):
        quotas = get_all_quotas()
        self.quota_table.setRowCount(len(quotas))
        for row, q in enumerate(quotas):
            remaining = q['total_quota'] - q['used_quota']
            self.quota_table.setItem(row, 0, QTableWidgetItem(str(q['member_id'])))
            self.quota_table.setItem(row, 1, QTableWidgetItem(q['member_name']))
            self.quota_table.setItem(row, 2, QTableWidgetItem(q['phone']))
            self.quota_table.setItem(row, 3, QTableWidgetItem(q['member_type']))
            self.quota_table.setItem(row, 4, QTableWidgetItem(str(q['total_quota'])))
            self.quota_table.setItem(row, 5, QTableWidgetItem(str(q['used_quota'])))
            rem_item = QTableWidgetItem(str(remaining))
            if remaining == 0:
                rem_item.setForeground(QBrush(QColor(220, 50, 50)))
            elif remaining <= 1:
                rem_item.setForeground(QBrush(QColor(230, 160, 30)))
            self.quota_table.setItem(row, 6, rem_item)
        if quotas:
            self.quota_table.selectRow(0)

    def on_member_selected(self):
        row = self.quota_table.currentRow()
        if row < 0:
            return
        member_id = int(self.quota_table.item(row, 0).text())
        bookings = get_member_bookings(member_id)
        self.booking_table.setRowCount(len(bookings))
        for r, b in enumerate(bookings):
            self.booking_table.setItem(r, 0, QTableWidgetItem(b['date']))
            self.booking_table.setItem(r, 1, QTableWidgetItem(f"{b['start_time']}-{b['end_time']}"))
            self.booking_table.setItem(r, 2, QTableWidgetItem(b['wall_name']))
            status_item = QTableWidgetItem(b['status'])
            if b['status'] == 'cancelled':
                status_item.setForeground(QBrush(QColor(150, 150, 150)))
            self.booking_table.setItem(r, 3, status_item)
            self.booking_table.setItem(r, 4, QTableWidgetItem("是" if b['use_quota'] else "否"))
            amt = f"¥{b['amount']:.2f}" if b['amount'] > 0 else "免费"
            self.booking_table.setItem(r, 5, QTableWidgetItem(amt))

    def reset_quotas(self):
        if QMessageBox.question(self, "确认",
                                "确定重置本月所有会员额度吗？\n额度将恢复为初始值，已使用次数清零。\n（每月1日自动重置，此操作用于手动补发）") == QMessageBox.StandardButton.Yes:
            reset_monthly_quotas()
            self.load_quotas()
            QMessageBox.information(self, "成功", "本月额度已重置")

    def add_member_dialog(self):
        dialog = MemberDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                add_member(data['name'], data['phone'], data['member_type'], data['monthly_quota'])
                self.load_members()
                self.load_quotas()
                QMessageBox.information(self, "成功", "会员已添加")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加失败：{e}")

    def edit_member_dialog(self):
        row = self.quota_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择会员")
            return
        member_id = int(self.quota_table.item(row, 0).text())
        member = next((m for m in self.members if m['id'] == member_id), None)
        if not member:
            return
        dialog = MemberDialog(self, member)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                update_member(member_id, data['name'], data['phone'],
                            data['member_type'], data['monthly_quota'])
                self.load_members()
                self.load_quotas()
                QMessageBox.information(self, "成功", "会员信息已更新")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"更新失败：{e}")


class MemberDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("会员信息")
        self.data = data or {}
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(self.data.get('name', ''))
        self.phone_edit = QLineEdit(self.data.get('phone', ''))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["normal", "vip"])
        if self.data.get('member_type'):
            idx = self.type_combo.findText(self.data['member_type'])
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        self.quota_spin = QSpinBox()
        self.quota_spin.setRange(1, 60)
        self.quota_spin.setValue(self.data.get('monthly_quota', 4))

        layout.addRow("姓名：", self.name_edit)
        layout.addRow("手机号：", self.phone_edit)
        layout.addRow("类型：", self.type_combo)
        layout.addRow("月度免费额度(次)：", self.quota_spin)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'phone': self.phone_edit.text().strip(),
            'member_type': self.type_combo.currentText(),
            'monthly_quota': self.quota_spin.value()
        }
