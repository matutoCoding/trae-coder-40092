from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QHeaderView,
                             QLabel, QGroupBox, QSpinBox, QDoubleSpinBox, QTabWidget)
from PyQt6.QtGui import QColor, QBrush
from services.transaction_service import (get_transactions, get_equipment_list,
                                           add_equipment, rent_equipment, return_equipment,
                                           get_rentals)
from services.quota_service import get_all_members
from services.booking_service import get_member_bookings


class TransactionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_booking_tab(), "预约记录")
        self.tabs.addTab(self._build_equipment_tab(), "装备租赁")
        self.tabs.addTab(self._build_tx_tab(), "消费流水")
        layout.addWidget(self.tabs)

    def _build_booking_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("预约记录 - 包含额度使用与自费消费"))
        bar.addStretch()
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_bookings)
        bar.addWidget(btn_refresh)
        layout.addLayout(bar)

        self.booking_table = QTableWidget()
        self.booking_table.setColumnCount(7)
        self.booking_table.setHorizontalHeaderLabels(
            ["ID", "会员", "岩壁道", "日期", "时段", "状态", "金额"]
        )
        self.booking_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.booking_table)
        return w

    def _build_equipment_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)

        eq_group = QGroupBox("装备管理")
        eq_layout = QVBoxLayout()
        self.equip_table = QTableWidget()
        self.equip_table.setColumnCount(4)
        self.equip_table.setHorizontalHeaderLabels(["ID", "名称", "库存", "单价/小时"])
        self.equip_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.equip_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        eq_layout.addWidget(self.equip_table)

        eq_btn_layout = QHBoxLayout()
        btn_add_eq = QPushButton("新增装备")
        btn_add_eq.clicked.connect(self.add_equipment_dialog)
        btn_rent = QPushButton("租赁")
        btn_rent.clicked.connect(self.rent_dialog)
        btn_return = QPushButton("归还选中")
        btn_return.clicked.connect(self.return_selected)
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_equipment)
        eq_btn_layout.addWidget(btn_add_eq)
        eq_btn_layout.addWidget(btn_rent)
        eq_btn_layout.addWidget(btn_return)
        eq_btn_layout.addWidget(btn_refresh)
        eq_layout.addLayout(eq_btn_layout)
        eq_group.setLayout(eq_layout)
        layout.addWidget(eq_group, 1)

        rental_group = QGroupBox("租赁记录")
        rental_layout = QVBoxLayout()
        self.rental_table = QTableWidget()
        self.rental_table.setColumnCount(6)
        self.rental_table.setHorizontalHeaderLabels(
            ["ID", "会员", "装备", "数量", "费用", "状态"]
        )
        self.rental_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rental_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        rental_layout.addWidget(self.rental_table)
        rental_group.setLayout(rental_layout)
        layout.addWidget(rental_group, 1)

        return w

    def _build_tx_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        bar = QHBoxLayout()
        self.total_label = QLabel("总流水：¥0.00")
        bar.addWidget(self.total_label)
        bar.addStretch()
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_transactions)
        bar.addWidget(btn_refresh)
        layout.addLayout(bar)

        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(6)
        self.tx_table.setHorizontalHeaderLabels(
            ["ID", "会员", "类型", "金额", "说明", "时间"]
        )
        self.tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tx_table)
        return w

    def refresh_all(self):
        self.refresh_bookings()
        self.refresh_equipment()
        self.refresh_rentals()
        self.refresh_transactions()

    def refresh_bookings(self):
        bookings = get_member_bookings()
        self.booking_table.setRowCount(len(bookings))
        for r, b in enumerate(bookings):
            self.booking_table.setItem(r, 0, QTableWidgetItem(str(b['id'])))
            self.booking_table.setItem(r, 1, QTableWidgetItem(b['member_name']))
            self.booking_table.setItem(r, 2, QTableWidgetItem(b['wall_name']))
            self.booking_table.setItem(r, 3, QTableWidgetItem(b['date']))
            self.booking_table.setItem(r, 4, QTableWidgetItem(f"{b['start_time']}-{b['end_time']}"))
            status_item = QTableWidgetItem(b['status'])
            if b['status'] == 'cancelled':
                status_item.setForeground(QBrush(QColor(150, 150, 150)))
            self.booking_table.setItem(r, 5, status_item)
            amt_item = QTableWidgetItem(f"¥{b['amount']:.2f}" if b['amount'] > 0 else "免费(额度)")
            if b['amount'] > 0:
                amt_item.setForeground(QBrush(QColor(50, 120, 200)))
            self.booking_table.setItem(r, 6, amt_item)

    def refresh_equipment(self):
        eq_list = get_equipment_list()
        self.equip_table.setRowCount(len(eq_list))
        for r, e in enumerate(eq_list):
            self.equip_table.setItem(r, 0, QTableWidgetItem(str(e['id'])))
            self.equip_table.setItem(r, 1, QTableWidgetItem(e['name']))
            stock_item = QTableWidgetItem(str(e['stock']))
            if e['stock'] <= 3:
                stock_item.setForeground(QBrush(QColor(220, 50, 50)))
            self.equip_table.setItem(r, 2, stock_item)
            self.equip_table.setItem(r, 3, QTableWidgetItem(f"¥{e['price_per_hour']:.2f}"))

    def refresh_rentals(self):
        rentals = get_rentals()
        self.rental_table.setRowCount(len(rentals))
        for r, rt in enumerate(rentals):
            self.rental_table.setItem(r, 0, QTableWidgetItem(str(rt['id'])))
            self.rental_table.setItem(r, 1, QTableWidgetItem(rt['member_name']))
            self.rental_table.setItem(r, 2, QTableWidgetItem(rt['equipment_name']))
            self.rental_table.setItem(r, 3, QTableWidgetItem(f"{rt['quantity']} x {rt['hours']}h"))
            self.rental_table.setItem(r, 4, QTableWidgetItem(f"¥{rt['amount']:.2f}"))
            status_item = QTableWidgetItem(rt['status'])
            if rt['status'] == 'active':
                status_item.setForeground(QBrush(QColor(50, 160, 80)))
            else:
                status_item.setForeground(QBrush(QColor(150, 150, 150)))
            self.rental_table.setItem(r, 5, status_item)

    def refresh_transactions(self):
        txs = get_transactions()
        self.tx_table.setRowCount(len(txs))
        total = 0.0
        for r, t in enumerate(txs):
            self.tx_table.setItem(r, 0, QTableWidgetItem(str(t['id'])))
            self.tx_table.setItem(r, 1, QTableWidgetItem(t['member_name']))
            self.tx_table.setItem(r, 2, QTableWidgetItem(t['type']))
            amt_item = QTableWidgetItem(f"¥{t['amount']:.2f}")
            if t['amount'] < 0:
                amt_item.setForeground(QBrush(QColor(220, 50, 50)))
            else:
                amt_item.setForeground(QBrush(QColor(50, 160, 80)))
            self.tx_table.setItem(r, 3, amt_item)
            self.tx_table.setItem(r, 4, QTableWidgetItem(t['description'] or ""))
            self.tx_table.setItem(r, 5, QTableWidgetItem(t['created_at']))
            total += t['amount']
        self.total_label.setText(f"总流水：¥{total:.2f}")

    def add_equipment_dialog(self):
        dialog = EquipmentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            add_equipment(data['name'], data['stock'], data['price'])
            self.refresh_equipment()
            QMessageBox.information(self, "成功", "装备已添加")

    def rent_dialog(self):
        row = self.equip_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择装备")
            return
        eq_id = int(self.equip_table.item(row, 0).text())
        eq_name = self.equip_table.item(row, 1).text()
        dialog = RentDialog(self, eq_id, eq_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            success, result = rent_equipment(data['member_id'], eq_id,
                                             data['quantity'], data['hours'])
            if success:
                self.refresh_equipment()
                self.refresh_rentals()
                self.refresh_transactions()
                QMessageBox.information(self, "成功", f"租赁成功，订单号：{result}")
            else:
                QMessageBox.warning(self, "失败", result)

    def return_selected(self):
        row = self.rental_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择租赁记录")
            return
        rental_id = int(self.rental_table.item(row, 0).text())
        status = self.rental_table.item(row, 5).text()
        if status != 'active':
            QMessageBox.warning(self, "提示", "该租赁已归还")
            return
        if QMessageBox.question(self, "确认", "确定归还该装备吗？") == QMessageBox.StandardButton.Yes:
            success, msg = return_equipment(rental_id)
            if success:
                self.refresh_equipment()
                self.refresh_rentals()
                QMessageBox.information(self, "成功", msg)
            else:
                QMessageBox.warning(self, "失败", msg)


class EquipmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增装备")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 1000)
        self.stock_spin.setValue(10)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1000)
        self.price_spin.setSingleStep(1)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(10)
        layout.addRow("名称：", self.name_edit)
        layout.addRow("库存：", self.stock_spin)
        layout.addRow("单价/小时(¥)：", self.price_spin)

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
            'stock': self.stock_spin.value(),
            'price': self.price_spin.value()
        }


class RentDialog(QDialog):
    def __init__(self, parent=None, eq_id=None, eq_name=""):
        super().__init__(parent)
        self.setWindowTitle(f"租赁 - {eq_name}")
        layout = QFormLayout(self)

        self.member_combo = QComboBox()
        for m in get_all_members():
            self.member_combo.addItem(f"{m['name']} ({m['phone']})", m['id'])
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 50)
        self.qty_spin.setValue(1)
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(1, 24)
        self.hour_spin.setValue(2)

        layout.addRow("选择会员：", self.member_combo)
        layout.addRow("数量：", self.qty_spin)
        layout.addRow("时长(小时)：", self.hour_spin)

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
            'member_id': self.member_combo.currentData(),
            'quantity': self.qty_spin.value(),
            'hours': self.hour_spin.value()
        }
