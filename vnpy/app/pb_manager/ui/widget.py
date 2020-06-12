from vnpy.trader.ui import QtWidgets
from vnpy.trader.engine import MainEngine, EventEngine

from ..engine import APP_NAME, PbManagerEngine
from ..constants import *
import os


class PbManagerWidget(QtWidgets.QWidget):
    """"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__()

        self.engine: PbManagerEngine = main_engine.get_engine(APP_NAME)

        self.path_edit = None
        self.position_table = None
        self.order_table = None
        self.stock_list_table = None
        self.total_money_label = None

        self.init_ui()

        # self.engine.file_path = self.path_edit.text()

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

        sell_button = QtWidgets.QPushButton("卖出")
        sell_button.clicked.connect(self.send_sell_order)

        buy_button = QtWidgets.QPushButton("买入")
        buy_button.clicked.connect(self.send_buy_order)

        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(refresh_button)
        hbox1.addWidget(path_button)
        hbox1.addWidget(self.path_edit)
        hbox1.addWidget(label1)
        hbox1.addWidget(self.total_money_label)
        hbox1.addWidget(sell_button)
        hbox1.addWidget(buy_button)

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(self.stock_list_table)
        hbox2.addWidget(self.order_table)
        hbox2.setStretchFactor(self.stock_list_table, 1)
        hbox2.setStretchFactor(self.order_table, 3)

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

    def init_stock_list_table(self) -> None:
        """"""
        labels = STOCK_FOR_BUY_COLUMN_NAMES

        self.stock_list_table = QtWidgets.QTableWidget()
        self.stock_list_table.setColumnCount(len(labels))
        self.stock_list_table.setHorizontalHeaderLabels(labels)
        self.stock_list_table.verticalHeader().setVisible(False)
        self.stock_list_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

    def send_sell_order(self):
        """"""
        if not os.path.isdir(self.path_edit.text()):
            QtWidgets.QMessageBox.information(self, "输入错误", '工作路径不是合法目录，请重新选择！')
            return None

        # 获取数据
        self.engine.init_data(self.path_edit.text())

        self.engine.generate_sell_order()

    def send_buy_order(self):
        """"""
        if not os.path.isdir(self.path_edit.text()):
            QtWidgets.QMessageBox.information(self, "输入错误", '工作路径不是合法目录，请重新选择！')
            return None

        # 获取数据
        self.engine.init_data(self.path_edit.text())

        self.engine.generate_buy_order()

    def set_work_path(self):
        """"""
        result: str = QtWidgets.QFileDialog.getExistingDirectory(
            caption="选取PB交易系统工作目录"
        )

        if result != '':
            self.path_edit.setText(result)
            self.engine.file_path = self.path_edit.text()

    def refresh_data(self):
        """"""
        if not os.path.isdir(self.path_edit.text()):
            QtWidgets.QMessageBox.information(self, '工作路径非法', '"工作路径"不是合法目录，请重新选择！')
            return None

        # 获取数据
        self.engine.init_data(self.path_edit.text())

        if self.engine.origin_pos is None:
            QtWidgets.QMessageBox.information(self, '文件名不正确', '文件不存在，请检查文件名是否符合格式：CC_STOCK_今天年月日.csv！')
            return None

        if self.engine.stock_list is None:
            QtWidgets.QMessageBox.information(self, '文件名不正确', '文件不存在，请检查是否存在：成分股.xlsx！')
            return None

        # 更新表格
        stock_list = self.engine.stock_list.reset_index()

        self.stock_list_table.setRowCount(0)
        self.stock_list_table.setRowCount(len(stock_list))

        for row in range(len(stock_list)):
            self.stock_list_table.setItem(row, 0, QtWidgets.QTableWidgetItem(stock_list.loc[row, 'code']))
            self.stock_list_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(stock_list.loc[row, 'weight'])))
            self.stock_list_table.setItem(row, 3, QtWidgets.QTableWidgetItem(stock_list.loc[row, 'exchange']))

        position = self.engine.origin_pos

        self.position_table.setRowCount(0)
        self.position_table.setRowCount(len(position))

        for row in range(len(position)):
            for col in range(len(position.columns)):
                self.position_table.setItem(row, col, QtWidgets.QTableWidgetItem(position.iloc[row, col]))

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


