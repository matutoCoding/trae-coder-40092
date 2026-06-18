from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QTextEdit, QMessageBox, QHeaderView,
                             QLabel, QDateEdit, QGroupBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QDate
from services.wall_service import (get_all_walls, add_wall, update_wall, delete_wall,
                                    get_available_slots, get_booked_slots)
from services.booking_service import create_booking, cancel_booking
from services.quota_service import get_all_members, ensure_member_quota


class WallScheduleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_walls()
        self.load_members()

    def init_ui(self):
        layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        wall_group = QGroupBox("岩壁道管理")
        wall_layout = QVBoxLayout()
        self.wall_table = QTableWidget()
        self.wall_table.setColumnCount(4)
        self.wall_table.setHorizontalHeaderLabels(["ID", "名称", "难度", "描述"])
        self.wall_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.wall_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.wall_table.itemSelectionChanged.connect(self.on_wall_selected)
        wall_layout.addWidget(self.wall_table)

        btn_layout = QHBoxLayout()
        self.btn_add_wall = QPushButton("新增岩壁道")
        self.btn_edit_wall = QPushButton("编辑")
        self.btn_del_wall = QPushButton("删除")
        self.btn_add_wall.clicked.connect(self.add_wall_dialog)
        self.btn_edit_wall.clicked.connect(self.edit_wall_dialog)
        self.btn_del_wall.clicked.connect(self.delete_wall)
        btn_layout.addWidget(self.btn_add_wall)
        btn_layout.addWidget(self.btn_edit_wall)
        btn_layout.addWidget(self.btn_del_wall)
        wall_layout.addLayout(btn_layout)
        wall_group.setLayout(wall_layout)
        left_panel.addWidget(wall_group)

        member_group = QGroupBox("选择会员")
        member_layout = QVBoxLayout()
        self.member_combo = QComboBox()
        member_layout.addWidget(self.member_combo)
        self.quota_label = QLabel("本月额度：-")
        member_layout.addWidget(self.quota_label)
        member_group.setLayout(member_layout)
        left_panel.addWidget(member_group)

        layout.addLayout(left_panel, 1)

        schedule_group = QGroupBox("时段排期与预约")
        schedule_layout = QVBoxLayout()

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("选择日期："))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.refresh_schedule)
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh_schedule)
        date_layout.addWidget(self.btn_refresh)
        schedule_layout.addLayout(date_layout)

        slot_layout = QHBoxLayout()

        avail_group = QGroupBox("可预约时段")
        avail_layout = QVBoxLayout()
        self.available_list = QListWidget()
        avail_layout.addWidget(self.available_list)
        self.btn_book = QPushButton("预约选中时段")
        self.btn_book.clicked.connect(self.book_slot)
        avail_layout.addWidget(self.btn_book)
        avail_group.setLayout(avail_layout)

        booked_group = QGroupBox("已预约时段")
        booked_layout = QVBoxLayout()
        self.booked_list = QListWidget()
        booked_layout.addWidget(self.booked_list)
        self.btn_cancel = QPushButton("取消选中预约")
        self.btn_cancel.clicked.connect(self.cancel_selected_booking)
        booked_layout.addWidget(self.btn_cancel)
        booked_group.setLayout(booked_layout)

        slot_layout.addWidget(avail_group)
        slot_layout.addWidget(booked_group)
        schedule_layout.addLayout(slot_layout)

        schedule_group.setLayout(schedule_layout)
        right_panel.addWidget(schedule_group)

        layout.addLayout(right_panel, 2)

    def load_walls(self):
        walls = get_all_walls()
        self.wall_table.setRowCount(len(walls))
        for row, w in enumerate(walls):
            self.wall_table.setItem(row, 0, QTableWidgetItem(str(w['id'])))
            self.wall_table.setItem(row, 1, QTableWidgetItem(w['name']))
            self.wall_table.setItem(row, 2, QTableWidgetItem(w['difficulty']))
            self.wall_table.setItem(row, 3, QTableWidgetItem(w['description'] or ""))
        if walls:
            self.wall_table.selectRow(0)

    def load_members(self):
        self.member_combo.clear()
        members = get_all_members()
        for m in members:
            self.member_combo.addItem(f"{m['name']} ({m['phone']})", m['id'])
        self.member_combo.currentIndexChanged.connect(self.update_quota_label)
        if members:
            self.update_quota_label()

    def update_quota_label(self):
        member_id = self.member_combo.currentData()
        if member_id:
            quota = ensure_member_quota(member_id)
            if quota:
                remaining = quota['total_quota'] - quota['used_quota']
                self.quota_label.setText(f"本月额度：剩余 {remaining}/{quota['total_quota']} 次")

    def get_selected_wall_id(self):
        row = self.wall_table.currentRow()
        if row < 0:
            return None
        return int(self.wall_table.item(row, 0).text())

    def on_wall_selected(self):
        self.refresh_schedule()

    def refresh_schedule(self):
        wall_id = self.get_selected_wall_id()
        if not wall_id:
            return
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        available = get_available_slots(wall_id, date_str)
        booked = get_booked_slots(wall_id, date_str)

        self.available_list.clear()
        for s in available:
            item = QListWidgetItem(f"{s['start']} - {s['end']}")
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.available_list.addItem(item)

        self.booked_list.clear()
        for b in booked:
            text = f"{b['start_time']} - {b['end_time']} | {b['member_name']}"
            if b['amount'] > 0:
                text += f" | 自费 ¥{b['amount']:.2f}"
            else:
                text += " | 免费额度"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, b)
            self.booked_list.addItem(item)

    def add_wall_dialog(self):
        dialog = WallDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            add_wall(data['name'], data['difficulty'], data['description'])
            self.load_walls()
            QMessageBox.information(self, "成功", "岩壁道已添加")

    def edit_wall_dialog(self):
        row = self.wall_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要编辑的岩壁道")
            return
        wall_id = int(self.wall_table.item(row, 0).text())
        data = {
            'name': self.wall_table.item(row, 1).text(),
            'difficulty': self.wall_table.item(row, 2).text(),
            'description': self.wall_table.item(row, 3).text()
        }
        dialog = WallDialog(self, data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            update_wall(wall_id, new_data['name'], new_data['difficulty'], new_data['description'])
            self.load_walls()
            QMessageBox.information(self, "成功", "岩壁道已更新")

    def delete_wall(self):
        row = self.wall_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要删除的岩壁道")
            return
        wall_id = int(self.wall_table.item(row, 0).text())
        if QMessageBox.question(self, "确认", "确定删除该岩壁道吗？") == QMessageBox.StandardButton.Yes:
            delete_wall(wall_id)
            self.load_walls()
            self.refresh_schedule()

    def book_slot(self):
        wall_id = self.get_selected_wall_id()
        if not wall_id:
            QMessageBox.warning(self, "提示", "请选择岩壁道")
            return
        member_id = self.member_combo.currentData()
        if not member_id:
            QMessageBox.warning(self, "提示", "请选择会员")
            return
        item = self.available_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请选择可预约时段")
            return
        slot = item.data(Qt.ItemDataRole.UserRole)
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        success, result = create_booking(member_id, wall_id, date_str, slot['start'], slot['end'])
        if success:
            self.refresh_schedule()
            self.update_quota_label()
            QMessageBox.information(self, "成功", f"预约成功！订单号：{result}")
        else:
            QMessageBox.warning(self, "失败", result)

    def cancel_selected_booking(self):
        item = self.booked_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请选择要取消的预约")
            return
        booking = item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "确认", f"确定取消 {booking['start_time']}-{booking['end_time']} 的预约吗？\n退订后时段将立即释放。") == QMessageBox.StandardButton.Yes:
            success, msg = cancel_booking(booking['id'])
            if success:
                self.refresh_schedule()
                self.update_quota_label()
                QMessageBox.information(self, "成功", msg)
            else:
                QMessageBox.warning(self, "失败", msg)


class WallDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("岩壁道信息")
        self.data = data or {}
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(self.data.get('name', ''))
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["初级", "中级", "高级"])
        if self.data.get('difficulty'):
            idx = self.diff_combo.findText(self.data['difficulty'])
            if idx >= 0:
                self.diff_combo.setCurrentIndex(idx)
        self.desc_edit = QTextEdit(self.data.get('description', ''))
        self.desc_edit.setFixedHeight(80)
        layout.addRow("名称：", self.name_edit)
        layout.addRow("难度：", self.diff_combo)
        layout.addRow("描述：", self.desc_edit)

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
            'difficulty': self.diff_combo.currentText(),
            'description': self.desc_edit.toPlainText().strip()
        }
