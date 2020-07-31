from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.engine import MainEngine, EventEngine

from ..engine import APP_NAME, PbManagerEngine
from ..constants import *
import os
import pandas as pd

from vnpy.trader.utility import load_json, save_json

class PbManagerWidget(QtWidgets.QWidget):
    """"""
    setting_filename = "pb_manager_setting.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__()

        self.engine: PbManagerEngine = main_engine.get_engine(APP_NAME)

        self.path_edit = None
        self.position_table = None
        self.order_table = None
        self.stock_list_table = None
        self.total_money_label = None
        self.buy_order_table = None
        self.sell_order_table = None
        self.tab_table = None
        self.rzrq_check = None

        self.init_ui()

        self.load_setting()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle("PB交易系统")

        self.init_position_table()
        self.init_stock_list_table()
        self.init_order_result_table()

        refresh_button = QtWidgets.QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_data)

        path_button = QtWidgets.QPushButton("设置工作路径")
        path_button.clicked.connect(self.set_work_path)

        self.path_edit = QtWidgets.QLineEdit()

        label1 = QtWidgets.QLabel()
        label1.setText("总资金(元):")

        self.total_money_label = QtWidgets.QLabel()
        self.total_money_label.setText('0.0')

        generate_sell_order = QtWidgets.QPushButton("生成卖单")
        generate_sell_order.clicked.connect(self.generate_sell_order)

        self.rzrq_check = QtWidgets.QCheckBox("融资融券")
        self.rzrq_check.setCheckState(QtCore.Qt.Checked)

        order_type_label = QtWidgets.QLabel()
        order_type_label.setText('委托类型:')

        self.order_type_combox = QtWidgets.QComboBox()
        self.order_type_combox.addItems(order_type.name for order_type in OrderType)

        sell_button = QtWidgets.QPushButton("卖出")
        sell_button.clicked.connect(self.send_sell_order)

        generate_buy_order = QtWidgets.QPushButton("生成买单")
        generate_buy_order.clicked.connect(self.generate_buy_order)

        buy_button = QtWidgets.QPushButton("买入")
        buy_button.clicked.connect(self.send_buy_order)

        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(refresh_button)
        hbox1.addWidget(path_button)
        hbox1.addWidget(self.path_edit)
        hbox1.addWidget(label1)
        hbox1.addWidget(self.total_money_label)
        hbox1.addWidget(self.rzrq_check)
        hbox1.addWidget(order_type_label)
        hbox1.addWidget(self.order_type_combox)
        hbox1.addWidget(generate_sell_order)
        hbox1.addWidget(sell_button)
        hbox1.addWidget(generate_buy_order)
        hbox1.addWidget(buy_button)

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(self.stock_list_table)
        hbox2.addWidget(self.tab_table)
        hbox2.setStretchFactor(self.stock_list_table, 1)
        hbox2.setStretchFactor(self.tab_table, 3)

        hbox3 = QtWidgets.QHBoxLayout()
        hbox3.addWidget(self.position_table)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)

        self.setLayout(vbox)
        self.showMaximized()

    def init_position_table(self) -> None:
        """"""
        labels = POSITION_COLUMN_NAMES

        self.position_table = QtWidgets.QTableWidget()
        self.position_table.setColumnCount(len(labels))
        self.position_table.setHorizontalHeaderLabels(labels)
        self.position_table.verticalHeader().setVisible(False)
        self.position_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

    def init_order_result_table(self) -> None:
        """"""
        labels = ORDER_RESULT_COLUMN_NAMES

        self.order_table = QtWidgets.QTableWidget()
        self.order_table.setColumnCount(len(labels))
        self.order_table.setHorizontalHeaderLabels(labels)
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

        self.buy_order_table = QtWidgets.QTableWidget()
        self.buy_order_table.setColumnCount(len(STOCK_FOR_BUY_ORDER_COLUMN_NAMES))
        self.buy_order_table.setHorizontalHeaderLabels(STOCK_FOR_BUY_ORDER_COLUMN_NAMES)
        self.buy_order_table.verticalHeader().setVisible(False)
        self.buy_order_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

        self.sell_order_table = QtWidgets.QTableWidget()
        self.sell_order_table.setColumnCount(len(STOCK_FOR_SELL_ORDER_COLUMN_NAMES))
        self.sell_order_table.setHorizontalHeaderLabels(STOCK_FOR_SELL_ORDER_COLUMN_NAMES)
        self.sell_order_table.verticalHeader().setVisible(False)
        self.sell_order_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

        # 允许弹出菜单
        self.buy_order_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.sell_order_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # 将信号请求连接到槽（单击鼠标右键，就调用方法）
        self.buy_order_table.customContextMenuRequested.connect(self.generate_pop_menu_for_buy)
        self.sell_order_table.customContextMenuRequested.connect(self.generate_pop_menu_for_sell)

        self.tab_table = QtWidgets.QTabWidget()
        self.tab_table.addTab(self.order_table, "委托")
        self.tab_table.addTab(self.sell_order_table, "卖出委托")
        self.tab_table.addTab(self.buy_order_table, "买入委托")
        self.tab_table.setTabPosition(QtWidgets.QTabWidget.South)

    def generate_pop_menu(
        self,
        pos: QtCore.QPoint,
        table: QtWidgets.QTableWidget,
    ):
        """生成右键菜单"""
        row_nums = []
        items = table.selectedItems()
        for num in range(len(items)):
            row_nums.append(table.row(items[num]))
        
        # 倒序删除，不会导致乱序的情况
        row_nums.sort(key=None, reverse=True)

        menu = QtWidgets.QMenu()
        itemAdd = menu.addAction("增加")
        itemDel = menu.addAction("删除")
        itemSellectAll = menu.addAction("全选")
        itemUnSellect = menu.addAction("反选")

        # 使菜单在正常位置显示
        screenPos = table.mapToGlobal(pos)

        maxRow = table.rowCount()

        # 单击一个菜单项就返回，使之被阻塞
        action = menu.exec(screenPos)
        if action == itemAdd:
            table.setRowCount(maxRow + 1)
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setCheckState(QtCore.Qt.Unchecked)
            table.setItem(maxRow, 0, checkbox)
            table.setItem(maxRow, 1, QtWidgets.QTableWidgetItem(""))
            table.setItem(maxRow, 2, QtWidgets.QTableWidgetItem(""))
            table.setItem(maxRow, 3, QtWidgets.QTableWidgetItem(""))
            table.setItem(maxRow, 4, QtWidgets.QTableWidgetItem(""))
            table.setItem(maxRow, 5, QtWidgets.QTableWidgetItem(""))

        if action == itemDel:
            for i in range(len(row_nums)):
                table.removeRow(row_nums[i])

        if action == itemSellectAll:
            for row in range(maxRow):
                table.item(row, 0).setCheckState(QtCore.Qt.Checked)

        if action == itemUnSellect:
            for row in range(maxRow):
                if table.item(row, 0).checkState() == QtCore.Qt.Unchecked:
                    table.item(row, 0).setCheckState(QtCore.Qt.Checked)
                else:
                    table.item(row, 0).setCheckState(QtCore.Qt.Unchecked)
        else:
            return

    def generate_pop_menu_for_buy(self, pos: QtCore.QPoint):
        """在买入委托生成右键菜单"""
        self.generate_pop_menu(pos, self.buy_order_table)

    def generate_pop_menu_for_sell(self, pos: QtCore.QPoint):
        """在卖出委托生成右键菜单"""
        self.generate_pop_menu(pos, self.sell_order_table)

    def init_stock_list_table(self) -> None:
        """初始化成分股列表"""
        labels = STOCK_FOR_BUY_COLUMN_NAMES

        self.stock_list_table = QtWidgets.QTableWidget()
        self.stock_list_table.setColumnCount(len(labels))
        self.stock_list_table.setHorizontalHeaderLabels(labels)
        self.stock_list_table.verticalHeader().setVisible(False)
        self.stock_list_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

    def generate_sell_order(self):
        """生成卖单列表"""
        if not os.path.isdir(self.path_edit.text()):
            QtWidgets.QMessageBox.information(self, "输入错误", '工作路径不是合法目录，请重新选择！')
            return None

        # 获取数据
        self.engine.init_data(self.path_edit.text(), self.rzrq_check.checkState())

        sell_order_list = self.engine.generate_sell_order_list().reset_index()

        self.sell_order_table.setRowCount(0)
        self.sell_order_table.setRowCount(len(sell_order_list))

        for row in range(len(sell_order_list)):
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setCheckState(QtCore.Qt.Checked)
            self.sell_order_table.setItem(row, 0, checkbox)
            self.sell_order_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(sell_order_list.iloc[row, 0]).strip()))
            self.sell_order_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(sell_order_list.iloc[row, 4]).strip()))
            self.sell_order_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(sell_order_list.iloc[row, 1]).strip()))
            self.sell_order_table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(int(sell_order_list.iloc[row, 2])).strip()))
            self.sell_order_table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(sell_order_list.iloc[row, 3]).strip()))

        self.tab_table.setCurrentIndex(1)

    def send_sell_order(self):
        """根据卖单列表生成委托文件给PB系统执行"""
        df = pd.DataFrame()

        # 获取tab中的数据
        for row in range(self.sell_order_table.rowCount()):
            if self.sell_order_table.item(row, 0).checkState() == QtCore.Qt.Checked:
                code = self.sell_order_table.item(row, 1).text()
                exchange = self.sell_order_table.item(row, 3).text()
                vol = int(self.sell_order_table.item(row, 4).text())
                price = round(float(self.sell_order_table.item(row, 5).text()), 2)
                data = pd.DataFrame([[code, exchange, vol, price]], columns=["code", "exchange", "vol", 'price'])
                df = df.append(data)

        if len(df) == 0:
            return None

        self.engine.generate_order(
            df.set_index('code'),
            self.rzrq_check.checkState(),
            Direction.SELL,
            self.order_type_combox.currentText()
        )

        self.refresh_data()
        self.tab_table.setCurrentIndex(0)

    def generate_buy_order(self):
        """生成买单列表"""
        if not os.path.isdir(self.path_edit.text()):
            QtWidgets.QMessageBox.information(self, "输入错误", '工作路径不是合法目录，请重新选择！')
            return None

        # 获取数据
        self.engine.init_data(self.path_edit.text(), self.rzrq_check.checkState())

        buy_order_list = self.engine.generate_buy_order_list().reset_index()

        self.buy_order_table.setRowCount(0)
        self.buy_order_table.setRowCount(len(buy_order_list))

        for row in range(len(buy_order_list)):
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setCheckState(QtCore.Qt.Checked)
            self.buy_order_table.setItem(row, 0, checkbox)
            self.buy_order_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(buy_order_list.iloc[row, 0]).strip()))
            self.buy_order_table.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
            self.buy_order_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(buy_order_list.iloc[row, 1]).strip()))
            self.buy_order_table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(int(buy_order_list.iloc[row, 2])).strip()))
            self.buy_order_table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(buy_order_list.iloc[row, 3]).strip()))

        self.tab_table.setCurrentIndex(2)

    def send_buy_order(self):
        """根据买单列表生成委托文件给PB系统执行"""
        df = pd.DataFrame()

        # 获取tab中的数据
        for row in range(self.buy_order_table.rowCount()):
            if self.buy_order_table.item(row, 0).checkState() == QtCore.Qt.Checked:
                code = self.buy_order_table.item(row, 1).text()
                exchange = self.buy_order_table.item(row, 3).text()
                vol = int(self.buy_order_table.item(row, 4).text())
                price = round(float(self.buy_order_table.item(row, 5).text()), 2)
                data = pd.DataFrame([[code, exchange, vol, price]], columns=["code", "exchange", "vol", 'price'])
                df = df.append(data)

        if len(df) == 0:
            return

        self.engine.generate_order(
            df.set_index('code'),
            self.rzrq_check.checkState(),
            Direction.BUY,
            self.order_type_combox.currentText()
        )

        self.refresh_data()
        self.tab_table.setCurrentIndex(0)

    def set_work_path(self):
        """"""
        result: str = QtWidgets.QFileDialog.getExistingDirectory(
            caption="选取PB交易系统工作目录"
        )

        if result != '':
            self.path_edit.setText(result)
            self.engine.file_path = self.path_edit.text()

        self.refresh_data()

    def refresh_data(self):
        """"""
        if not os.path.isdir(self.path_edit.text()):
            QtWidgets.QMessageBox.information(self, '工作路径非法', '"工作路径"不是合法目录，请重新选择！')
            return None

        # 获取数据
        self.engine.init_data(self.path_edit.text(), self.rzrq_check.checkState())

        if self.engine.origin_pos is None:
            QtWidgets.QMessageBox.information(self, '文件名不正确', '文件不存在，请检查文件名是否符合格式：CC_STOCK_今天年月日.csv！')
            return None

        if self.engine.stock_list is None:
            QtWidgets.QMessageBox.information(self, '文件名不正确', '文件不存在，请检查是否存在：成分股.xlsx！')
            return None

        # 更新成分股
        stock_list = self.engine.stock_list.reset_index()

        self.stock_list_table.setRowCount(0)
        self.stock_list_table.setRowCount(len(stock_list))

        for row in range(len(stock_list)):
            self.stock_list_table.setItem(row, 0, QtWidgets.QTableWidgetItem(stock_list.loc[row, 'code']))
            self.stock_list_table.setItem(row, 1, QtWidgets.QTableWidgetItem(stock_list.loc[row, 'name']))
            self.stock_list_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(stock_list.loc[row, 'weight'])))
            self.stock_list_table.setItem(row, 3, QtWidgets.QTableWidgetItem(stock_list.loc[row, 'exchange']))

        # 更新持仓
        position = self.engine.origin_pos

        self.position_table.setRowCount(0)
        self.position_table.setRowCount(len(position))

        for row in range(len(position)):
            for col in range(len(position.columns)):
                self.position_table.setItem(row, col, QtWidgets.QTableWidgetItem(position.iloc[row, col]))

        # 更新委托单
        df = self.engine.get_order_result()

        if df is None:
            QtWidgets.QMessageBox.information(self, '文件名不正确', '文件不存在，请检查文件名是否符合格式：XHPT_WT今天年月日.dbf！')
            return None

        self.order_table.setRowCount(0)
        self.order_table.setRowCount(len(df))

        for row in range(len(df)):
            for col in range(len(df.columns)):
                self.order_table.setItem(row, col, QtWidgets.QTableWidgetItem(str(df.iloc[row, col]).strip()))

        self.total_money_label.setText('{:,}'.format(self.engine.total_money))

        self.save_setting()

    def load_setting(self):
        """"""
        setting = load_json(self.setting_filename)
        if not setting:
            return

        self.path_edit.setText(setting["work_path"])
        self.rzrq_check.setCheckState(setting["account_type"])
        self.order_type_combox.setCurrentText(setting["order_type"])

    def save_setting(self):
        """"""
        setting = {
            "work_path": self.path_edit.text(),
            "account_type": self.rzrq_check.checkState(),
            "order_type": self.order_type_combox.currentText(),
        }

        save_json(self.setting_filename, setting)


