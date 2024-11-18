# models/backtesting/__init__.py

from .test_Backtesting_BuyandHold import run_buyandhold_backtest, plot_results_with_forecast as plot_buyandhold
from .test_Backtesting_DCA import run_dca_backtest, calculate_statistics, plot_results_with_forecast as plot_dca
from .test_Backtesting_maCross11 import MACrossBacktester
from .test_Backtesting_momentum import MomentumBacktester
from .testFGI import FGBacktest

__all__ = [
    'run_buyandhold_backtest', 'plot_buyandhold',
    'run_dca_backtest', ' calculate_statistics','plot_dca',
    'MACrossBacktester',
    'MomentumBacktester',
    'FGBacktest'
]


