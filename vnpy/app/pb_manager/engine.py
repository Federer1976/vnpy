from vnpy.trader.engine import BaseEngine, MainEngine, EventEngine
from QUANTAXIS.QAFetch.QATdx import QA_fetch_get_stock_realtime

from PyQt5 import QtCore

import os
import pandas as pd
import numpy as np
from .utils import *
from .constants import *

APP_NAME = "PbManager"


class PbManagerEngine(BaseEngine):
    """"""

    def __init__(
            self,
            main_engine: MainEngine,
            event_engine: EventEngine,
    ):
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)
        self.position: pd.DataFrame = None  # 当前持仓
        self.available_capital: float = 0.0  # 可用资金
        self.total_money: float = 0.0  # 总资金
        self.stock_list: pd.DataFrame = None
        self.file_path: str = ''
        self.origin_pos: pd.DataFrame = None  # 持仓原始数据

    def init_data(
            self,
            file_path: str,
            rzrq_state: QtCore.Qt.CheckState,
            strCPBH: str = '90530001',
            strZCDYBH: str = '1',
            strZHBH: str = '1',
    ) -> None:
        """
        初始化数据
        :param file_path: 数据所在路径
        :return: None
        """
        self.file_path = file_path

        self.get_position_from_pb(self.file_path + os.sep +
                                  (POSITION_FILENAME.replace('STOCK',
                                                            'RZRQ') if rzrq_state == QtCore.Qt.Checked else POSITION_FILENAME))
        self.get_stock_list_for_buy(self.file_path + os.sep +
                                    (INPUT_FILENAME.replace('STOCK',
                                                           'RZRQ') if rzrq_state == QtCore.Qt.Checked else INPUT_FILENAME))
        self.get_total_capital_from_pb(self.file_path + os.sep +
                                       (CAPITAL_FILENAME.replace('STOCK',
                                                                'RZRQ') if rzrq_state == QtCore.Qt.Checked else CAPITAL_FILENAME))

        self._strCPBH = strCPBH  # C32	产品代码/基金代码
        self._strZCDYBH = strZCDYBH  # C16	单元编号/组合编号
        self._strZHBH = strZHBH  # C16	组合编号

    def get_position_from_pb(
            self,
            filename: str,
    ) -> pd.DataFrame:
        """
        获取持仓股票列表
        :param filename: 文件名
        :return: DataFrame，数据列名：['code', 'available_vol', 'exchange']
        """
        try:
            df = pd.read_csv(filename, sep=',', encoding="gbk", header=0,
                             dtype=object)
            self.origin_pos = df

        except Exception as e:
            print(e)
            return None

        try:
            df = pd.read_csv(filename, sep=',', encoding="gbk", header=0,
                             usecols=[3, 4, 12, 18],  # ['证券代码', '持仓数量', '交易市场', '证券名称']
                             dtype=object,
                             names=['code', 'name', 'available_vol', 'exchange'])
        except Exception as e:
            print(e)
            return None

        df['code'] = df.loc[:, 'code'].str.zfill(6)
        df['available_vol'] = df['available_vol'].astype(np.int32)
        df['exchange'] = df.loc[:, 'exchange'] \
            .str.replace(r'(.+)',
                         repl=lambda m: Exchange.SSE
                         if m.group(0) == '上交所A' else Exchange.SZSE)

        self.position = df[df.available_vol != 0].set_index('code')
        return self.position

    def get_stock_list_for_buy(
            self,
            filename: str,
    ) -> pd.DataFrame:
        """
        获取购买的股票列表及股票权重
        :param filename: 文件名
        :return: DataFrame，数据列名：['code', 'weight', 'exchange', 'name']
        """
        try:
            df = pd.read_excel(filename).dropna(thresh=2)

        except Exception as e:
            print(e)
            return None

        # df = df.set_index('code').groupby(level='code').sum().reset_index()

        temp = df.loc[:, 'code'].str.extract(r'([0-9]+).([A-Z]+)')

        df['code'] = temp[0]

        df['exchange'] = temp.loc[:, 1] \
            .str.replace(r'([A-Z]{2})',
                         repl=lambda m: Exchange.SSE if m.group(
                             0) == 'SH' else Exchange.SZSE)
        self.stock_list = df[['code', 'weight', 'exchange', 'name']].set_index('code')

        return (self.stock_list)

    def get_total_capital_from_pb(
            self,
            filename: str,
    ) -> float:
        """
        get total capital.
        :return: float, total capital
        """
        try:
            capital = pd.read_csv(filename, sep=',', encoding="gbk")
            self.available_capital = capital.loc[0, '可用余额']
            self.total_money = capital.loc[0, '单元净值']
            return self.total_money

        except Exception as e:
            print(e)
            return None

    def generate_sell_order_list(self):
        """
        根据股票持仓及买入需求，生成股票卖出指令
        :return:
        """
        position = self.position
        stock_list_for_buy = self.stock_list
        money = self.total_money

        if position is None or stock_list_for_buy is None or money is None:
            print('数据源有问题，请检查数据源！')
            return None

        stock_price = QA_fetch_get_stock_realtime(stock_list_for_buy.index.tolist(),
                                                  ip='120.234.57.15', port=7709).reset_index().set_index('code')

        stock_list_for_buy['vol_for_buy'] = money * stock_list_for_buy['weight'] / stock_price['price']

        position['real_vol'] = position['available_vol'] - stock_list_for_buy['vol_for_buy']
        position['price'] = stock_price['price']
        sell_list = position.fillna(value={'real_vol': position['available_vol']})

        sell_list = sell_list[sell_list['real_vol'] > 0]

        stock_price = QA_fetch_get_stock_realtime(sell_list.index.tolist(),
                                                  ip='120.234.57.15', port=7709).reset_index().set_index('code')
        sell_list['price'] = stock_price['price']
        sell_list = split_order(sell_list)

        # return sell_list[sell_list['vol'] > 0]
        return sell_list

    def generate_sell_order(
            self,
            sell_list: pd.DataFrame,
            rzrq_state: QtCore.Qt.CheckState
    ):
        """
        根据股票持仓及买入需求，生成股票卖出指令
        :return:
        """
        if rzrq_state == QtCore.Qt.Checked:
            self._strCPBH = '1040'  # C32	产品代码/基金代码
            self._strZCDYBH = '1'  # C16	单元编号/组合编号
            self._strZHBH = '1'  # C16	组合编号

        sell_order = []

        for n in range(len(sell_list)):
            sell_order += [{'CPBH': self._strCPBH,  # C32 产品代码/基金代码
                            'ZCDYBH': self._strZCDYBH,  # C16 单元编号/组合编号
                            'ZHBH': self._strZHBH,  # C16 组合编号
                            'GDDM': dictGDDM[sell_list.iloc[n]['exchange']],  # C20 股东代码
                            'JYSC': sell_list.iloc[n]['exchange'],  # C3  交易市场
                            'ZQDM': sell_list.index[n],  # C16 证券代码
                            'WTFX': Direction.SELL,  # C4  委托方向
                            'WTJGLX': dictWTJGLX[sell_list.iloc[n]['exchange']],  # C1  委托价格类型
                            'WTJG': sell_list.iloc[n]['price'],  # N11.4	委托价格
                            'WTSL': sell_list.iloc[n]['vol'],  # N12 委托数量
                            'WBZDYXH': get_serial_no()}]  # N9  第三方系统自定义号

        return write_wt_dbf(self.file_path + os.sep + PB_WT_FILENAME, sell_order)

    def generate_buy_order_list(self):
        """
        根据持仓情况生成买入指令
        :return:
        """
        position = self.position
        stock_list_for_buy = self.stock_list
        money = self.total_money

        if position is None or stock_list_for_buy is None or money is None:
            print('数据源有问题，请检查数据源！')
            return None

        stock_price = QA_fetch_get_stock_realtime(stock_list_for_buy.index.tolist(),
                                                  ip='120.234.57.15', port=7709).reset_index().set_index('code')
        # stock_price = stock_price[stock_price['price'] != 0]

        stock_list_for_buy['vol_for_buy'] = money * stock_list_for_buy['weight'] / stock_price['price']

        stock_list_for_buy = stock_list_for_buy[np.isinf(stock_list_for_buy['vol_for_buy']) == False]
        stock_list_for_buy['real_vol'] = stock_list_for_buy['vol_for_buy'] - position['available_vol']

        buy_list = stock_list_for_buy.fillna(value={'real_vol': stock_list_for_buy['vol_for_buy']})
        buy_list['price'] = stock_price['price']

        buy_list = buy_list[buy_list['real_vol'] > 0]

        buy_list = split_order(buy_list)

        return buy_list

    def generate_buy_order(
            self,
            buy_list: pd.DataFrame,
            rzrq_state: QtCore.Qt.CheckState
    ):
        """
        根据持仓情况生成买入指令
        :return:
        """
        # position = self.position
        # stock_list_for_buy = self.stock_list
        # money = self.total_money
        #
        # if position is None or stock_list_for_buy is None or money is None:
        #     print('数据源有问题，请检查数据源！')
        #     return None
        #
        # stock_price = QA_fetch_get_stock_realtime(stock_list_for_buy.index.tolist(),
        #                                           ip='120.234.57.15', port=7709).reset_index().set_index('code')
        # # stock_price = stock_price[stock_price['price'] != 0]
        #
        # stock_list_for_buy['vol_for_buy'] = money * stock_list_for_buy['weight'] / stock_price['price']
        #
        # stock_list_for_buy = stock_list_for_buy[np.isinf(stock_list_for_buy['vol_for_buy']) == False]
        # stock_list_for_buy['real_vol'] = stock_list_for_buy['vol_for_buy'] - position['available_vol']
        #
        # buy_list = stock_list_for_buy.fillna(value={'real_vol': stock_list_for_buy['vol_for_buy']})
        # buy_list['price'] = stock_price['price']
        #
        # buy_list = buy_list[buy_list['real_vol'] > 0]
        #
        # buy_list = split_order(buy_list)

        if rzrq_state == QtCore.Qt.Checked:
            self._strCPBH = 1040  # C32	产品代码/基金代码
            self._strZCDYBH = 1  # C16	单元编号/组合编号
            self._strZHBH = 1  # C16	组合编号

        buy_order = []
        for n in range(len(buy_list)):
            buy_order += [{'CPBH': self._strCPBH,  # C32 产品代码/基金代码
                           'ZCDYBH': self._strZCDYBH,  # C16 单元编号/组合编号
                           'ZHBH': self._strZHBH,  # C16 组合编号
                           'GDDM': dictGDDM[buy_list.iloc[n]['exchange']],  # C20 股东代码
                           'JYSC': buy_list.iloc[n]['exchange'],  # C3  交易市场
                           'ZQDM': buy_list.index[n],  # C16 证券代码
                           'WTFX': Direction.BUY,  # C4  委托方向
                           'WTJGLX': dictWTJGLX[buy_list.iloc[n]['exchange']],  # C1  委托价格类型
                           'WTJG': buy_list.iloc[n]['price'],  # N11.4	委托价格
                           'WTSL': buy_list.iloc[n]['vol'],  # N12 委托数量
                           'WBZDYXH': get_serial_no()}]  # N9  第三方系统自定义号

        return write_wt_dbf(self.file_path + os.sep + PB_WT_FILENAME, buy_order)

    def generate_order(
            self,
            order_list: pd.DataFrame,
            rzrq_state: QtCore.Qt.CheckState,
            order_direction: Direction,
            order_type: OrderType,
    ):
        """
        根据持仓情况生成买入指令
        :return:
        """
        if rzrq_state == QtCore.Qt.Checked:
            self._strCPBH = '90530001'  # C32	产品代码/基金代码
            self._strZCDYBH = '3'  # C16	单元编号/组合编号
            self._strZHBH = '3'  # C16	组合编号
        else:
            self._strCPBH = '90530001'  # C32	产品代码/基金代码
            self._strZCDYBH = '1'  # C16	单元编号/组合编号
            self._strZHBH = '1'  # C16	组合编号

        order_dict = []
        for n in range(len(order_list)):
            if order_type == OrderType.FIVE_PRICE_CANCEL.name and \
                    order_list.iloc[n]['exchange'] == Exchange.SZSE:
                real_order_type = 'A'
            else:
                for ot in OrderType:
                    if ot.name == order_type:
                        real_order_type = ot.value

            if order_list.iloc[n]['exchange'] == Exchange.SZSE:
                if rzrq_state == QtCore.Qt.Checked:
                    gddm = '0899225880'
                else:
                    gddm = '0899225880'
            else:
                if rzrq_state == QtCore.Qt.Checked:
                    gddm = 'B883246832'
                else:
                    gddm = 'B883246832'

            # if order_list.index[n][:3] == '688':
            #     real_order_type = 'A'

            order_dict += [{'CPBH': self._strCPBH,                   # C32 产品代码/基金代码
                            'ZCDYBH': self._strZCDYBH,               # C16 单元编号/组合编号
                            'ZHBH': self._strZHBH,                   # C16 组合编号
                            'GDDM': gddm,                            # C20 股东代码
                            'JYSC': order_list.iloc[n]['exchange'],  # C3  交易市场
                            'ZQDM': order_list.index[n],        # C16 证券代码
                            'WTFX': order_direction.value,      # C4  委托方向
                            'WTJGLX': real_order_type,          # C1  委托价格类型
                            'WTJG': 0,                          # N11.4	委托价格
                            'WTSL': order_list.iloc[n]['vol'],  # N12 委托数量
                            'WBZDYXH': get_serial_no()}]        # N9  第三方系统自定义号

        return write_wt_dbf(self.file_path + os.sep + PB_WT_FILENAME, order_dict)

    def get_order_result(self) -> pd.DataFrame:

        filename = self.file_path + os.sep + PB_WT_FILENAME

        return read_dbf(filename)
