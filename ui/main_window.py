from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.wall_schedule import WallScheduleTab
from ui.quota_tab import QuotaTab
from ui.transaction_tab import TransactionTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("攀岩馆场次预约管理系统")
        self.resize(1280, 800)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        title = QLabel("攀岩馆场次预约管理系统")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("padding: 10px; color: #2c3e50;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(WallScheduleTab(), "岩壁道排期 & 预约")
        self.tabs.addTab(QuotaTab(), "额度管控 & 会员")
        self.tabs.addTab(TransactionTab(), "消费明细 & 装备")
        layout.addWidget(self.tabs)

        self.setCentralWidget(central)
