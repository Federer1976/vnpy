from pathlib import Path
from vnpy.trader.app import BaseApp
from .engine import OptionEngine, APP_NAME


class OptionMasterApp(BaseApp):
    """
    期权波动率交易（Option Volatility Trading），
    通过期权链中的诸多期权合约，围绕标的物二阶风险（波动率），构建立体化的量化交易策略
    """
    app_name = APP_NAME
    app_module = __module__
    app_path = Path(__file__).parent
    display_name = "期权交易"
    engine_class = OptionEngine
    widget_name = "OptionManager"
    icon_name = "option.ico"
