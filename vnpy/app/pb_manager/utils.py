# -*- coding : utf-8 -*-
# coding: utf-8

import pandas as pd
import dbf
import math
from collections import OrderedDict
from datetime import datetime

from .constants import *

INPUT_FILENAME = '成分股.xlsx'

PB_WT_FILENAME = 'XHPT_WT' + str(datetime.now().date()).replace('-', '') + '.dbf'
PB_WTCX_FILENAME = 'XHPT_WTCX' + str(datetime.now().date()).replace('-', '') + '.dbf'
PB_WTMX_FILENAME = 'XHPT_WTMX' + str(datetime.now().date()).replace('-', '') + '.dbf'
PB_CJCX_FILENAME = 'XHPT_CJCX' + str(datetime.now().date()).replace('-', '') + '.dbf'
PB_CD_FILENAME = 'XHPT_CD' + str(datetime.now().date()).replace('-', '') + '.dbf'

CAPITAL_FILENAME = 'ZJ_STOCK_' + str(datetime.now().date()).replace('-', '') + '.csv'
POSITION_FILENAME = 'CC_STOCK_' + str(datetime.now().date()).replace('-', '') + '.csv'

dictGDDM = {Exchange.SSE: 'A187702503', Exchange.SZSE: '0147434049'}  # C20	股东代码
dictWTJGLX = {Exchange.SSE: 'a', Exchange.SZSE: 'A'}  # C1委托价格类型

MAX_ORDER_VOL = 50000  # 每个订单最大不超过500手


def get_serial_no():
    """
    生成一个随机序列号
    :return: int 序列号
    """
    from random import randint

    n = 9

    start = 10 ** (n - 1)
    end = (10 ** n) - 1
    return randint(start, end)


def read_dbf(filename: str):
    """
    Convert file formate from dbf(dBase III plus) to DataFrame
    :param filename: the file name of dbf
    :return: DataFrame
    """
    if filename[-3:] != 'dbf':
        return None

    try:
        table = dbf.Table(filename, codepage="cp936")
        table.open()

        data = []

        for record in table:
            row = []
            for n in range(table.field_count):
                row.append((table.field_names[n], record[n]))
            data.append(OrderedDict(row))

        table.close()

        return pd.DataFrame(data)

    except Exception as e:
        print(e)
        return None


def write_wt_dbf(filename: str, data: list):
    """
    根据模版重新写入数据
    :param filename: 文件名
    :param data: 待写入的数据
    :return:
    """
    if filename[-3:] != 'dbf':
        return None

    try:
        table = dbf.Table(filename)

        table.open(mode=dbf.DbfStatus.READ_WRITE)

        # empty the dbf file
        # for record in table:
        #     dbf.delete(record)
        table.zap()

        for subrecord in data:
            table.append(subrecord)

        table.close()

    except Exception as e:
        print(e)
        return None


def split_order(data: pd.DataFrame):
    """
    将大单分拆成小单
    :param data: DataFrame:[code', 'real_vol']
    :return:DataFrame:[code', 'exchange', 'vol']
    """
    # Added for soloving this problem "A value is trying to be set on a copy of a slice from a DataFrame."
    origin_data = data.copy()
    # data['real_vol'] = data['real_vol'].transform(lambda x: math.floor(x / 100) * 100)

    origin_data['real_vol'] = origin_data['real_vol'].transform(lambda x: math.floor(x / 100) * 100)

    standard_order_num = origin_data['real_vol'].transform(lambda x: x // MAX_ORDER_VOL)
    standard_order_num = standard_order_num[standard_order_num > 0]

    origin_data['vol'] = origin_data['real_vol'].transform(lambda x: x % MAX_ORDER_VOL)

    new_order = pd.DataFrame(columns=origin_data.reset_index().columns).set_index('code')

    for n in range(len(standard_order_num)):
        row = origin_data.loc[standard_order_num.index[n]].copy()
        row['vol'] = MAX_ORDER_VOL
        rows = []
        for i in range(standard_order_num[n]):
            rows.append(row)
        new_order = new_order.append(pd.DataFrame(rows))

    df = origin_data.append(new_order)

    return df[['exchange', 'vol']]


# def get_sell_stock_list(filename=WORK_PATH + POSITION_FILENAME):
#     """
#     获取售卖的股票列表
#     :param filename: 文件名
#     :return: DataFrame，数据列名：['code', 'available_vol', 'exchange']
#     """
#     try:
#         df = pd.read_csv(filename, sep=',', encoding="gbk", header=0,
#                          usecols=[3, 14, 18],  # ['证券代码', '可用数量', '交易市场']
#                          dtype=object,
#                          names=['code', 'available_vol', 'exchange'])
#     except Exception as e:
#         print(e)
#         return None
#
#     df['code'] = df.loc[:, 'code'].str.zfill(6)
#     df['available_vol'] = df['available_vol'].astype(np.int32)
#     df['exchange'] = df.loc[:, 'exchange'].str.replace(r'(.+)',
#                                                        repl=lambda m: cons.Exchange.SSE if m.group(
#                                                            0) == '上交所A' else cons.Exchange.SZSE)
#     # 另外一种方式：通过replace进行替换
#     # df['exchange'] = df['exchange'].replace('上交所A', cons.Exchange.SSE)
#
#     return (df[df.available_vol != 0].set_index('code'))
#
#
# def get_buy_stock_list(filename=WORK_PATH + INPUT_FILENAME):
#     """
#     获取购买的股票列表及股票权重
#     :param filename: 文件名
#     :return: DataFrame，数据列名：['code', 'weight', 'exchange']
#     """
#     try:
#         df = pd.read_excel(filename).dropna(thresh=2)
#     except Exception as e:
#         print(e)
#         return None
#
#     df = df.set_index('code').groupby(level='code').sum().reset_index()
#
#     temp = df.loc[:, 'code'].str.extract(r'([0-9]+).([A-Z]+)')
#
#     df['code'] = temp[0]
#
#     df['exchange'] = temp.loc[:, 1].str.replace(r'([A-Z]{2})',
#                                                 repl=lambda m: cons.Exchange.SSE if m.group(
#                                                     0) == 'SH' else cons.Exchange.SZSE)
#
#     return (df[['code', 'weight', 'exchange']].set_index('code'))
#
#
# def get_total_capital(filename=WORK_PATH + CAPITAL_FILENAME):
#     """
#     get total capital.
#     :return: float, total capital
#     """
#     try:
#         capital = pd.read_csv(filename, sep=',', encoding="gbk")
#         return (capital.loc[0, '可用余额'])
#     except Exception as e:
#         print(e)
#         return None
#
#
# def generate_sell_order():
#     """
#     根据股票持仓及买入需求，生成股票卖出指令
#     :return:
#     """
#     position = get_sell_stock_list()
#     stock_list_for_buy = get_buy_stock_list()
#     money = get_total_capital()
#
#     if position is None or stock_list_for_buy is None or money is None:
#         print('数据源有问题，请检查数据源！')
#         return None
#
#     stock_price = QA_fetch_get_stock_realtime(stock_list_for_buy.index.tolist(),
#                                               ip='120.234.57.15', port=7709).reset_index().set_index('code')
#
#     stock_list_for_buy['vol_for_buy'] = money * stock_list_for_buy['weight'] / stock_price['price']
#
#     position['real_vol'] = position['available_vol'] - stock_list_for_buy['vol_for_buy']
#
#     sell_list = position[position['real_vol'] > 0]
#
#     sell_list = split_order(sell_list)
#
#     sell_order = []
#     for n in range(len(sell_list)):
#         sell_order += [{'CPBH': strCPBH,  # C32 产品代码/基金代码
#                         'ZCDYBH': strZCDYBH,  # C16 单元编号/组合编号
#                         'ZHBH': strZHBH,  # C16 组合编号
#                         'GDDM': dictGDDM[sell_list.iloc[n]['exchange']],  # C20 股东代码
#                         'JYSC': sell_list.iloc[n]['exchange'],  # C3  交易市场
#                         'ZQDM': sell_list.index[n],  # C16 证券代码
#                         'WTFX': cons.Direction.SELL,  # C4  委托方向
#                         'WTJGLX': dictWTJGLX[sell_list.iloc[n]['exchange']],  # C1  委托价格类型
#                         'WTJG': stock_price.loc[sell_list.index[n]]['price'],  # N11.4	委托价格
#                         'WTSL': sell_list.iloc[n]['vol'],  # N12 委托数量
#                         'WBZDYXH': get_serial_no()}]  # N9  第三方系统自定义号
#
#     return write_wt_dbf(WORK_PATH + PB_WT_FILENAME, sell_order)
#
#
# def generate_buy_order():
#     """
#     根据持仓情况生成买入指令
#     :return:
#     """
#     position = get_sell_stock_list()
#     stock_list_for_buy = get_buy_stock_list()
#     money = get_total_capital()
#
#     if position is None or stock_list_for_buy is None or money is None:
#         print('数据源有问题，请检查数据源！')
#         return None
#
#     stock_price = QA_fetch_get_stock_realtime(stock_list_for_buy.index.tolist(),
#                                               ip='120.234.57.15', port=7709).reset_index().set_index('code')
#     # stock_price = stock_price[stock_price['price'] != 0]
#
#     stock_list_for_buy['vol_for_buy'] = money * stock_list_for_buy['weight'] / stock_price['price']
#
#     stock_list_for_buy = stock_list_for_buy[np.isinf(stock_list_for_buy['vol_for_buy']) == False]
#     stock_list_for_buy['real_vol'] = stock_list_for_buy['vol_for_buy'] - position['available_vol']
#
#     buy_list = stock_list_for_buy.fillna(value={'real_vol': stock_list_for_buy['vol_for_buy']})
#
#     buy_list = buy_list[buy_list['real_vol'] > 0]
#
#     buy_list = split_order(buy_list)
#
#     buy_order = []
#     for n in range(len(buy_list)):
#         buy_order += [{'CPBH': strCPBH,  # C32 产品代码/基金代码
#                        'ZCDYBH': strZCDYBH,  # C16 单元编号/组合编号
#                        'ZHBH': strZHBH,  # C16 组合编号
#                        'GDDM': dictGDDM[buy_list.iloc[n]['exchange']],  # C20 股东代码
#                        'JYSC': buy_list.iloc[n]['exchange'],  # C3  交易市场
#                        'ZQDM': buy_list.index[n],  # C16 证券代码
#                        'WTFX': cons.Direction.BUY,  # C4  委托方向
#                        'WTJGLX': dictWTJGLX[buy_list.iloc[n]['exchange']],  # C1  委托价格类型
#                        'WTJG': stock_price.loc[buy_list.index[n]]['price'],  # N11.4	委托价格
#                        'WTSL': buy_list.iloc[n]['vol'],  # N12 委托数量
#                        'WBZDYXH': get_serial_no()}]  # N9  第三方系统自定义号
#
#     return write_wt_dbf(WORK_PATH + PB_WT_FILENAME, buy_order)
#
#
# if __name__ == '__main__':
#     # generate_sell_order()
#     generate_buy_order()
#     # df = read_dbf(WORK_PATH + PB_WT_FILENAME)
#     # print(df)
