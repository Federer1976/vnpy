from pathlib import Path

from vnpy.trader.app import BaseApp
from .engine import APP_NAME, PbManagerEngine


class PbManagerApp(BaseApp):
    """"""

    app_name = APP_NAME
    app_module = __module__
    app_path = Path(__file__).parent
    display_name = "PB交易系统"
    engine_class = PbManagerEngine
    widget_name = "PbManagerWidget"
    icon_name = "pb_manager.ico"
