# models/__init__.py

from .model import fetch_stock_prices, set_asset, calculate_required_return_api, search_ticker
from .corMatrix import calculate_correlation_matrix, plot_correlation_matrix 
from .backtesting import (
    run_buyandhold_backtest, plot_buyandhold,
    run_dca_backtest, calculate_statistics, plot_dca,
    MACrossBacktester, 
    MomentumBacktester,
    FGBacktest
)

__all__ = [
    'fetch_stock_prices', 'set_asset', 'calculate_required_return_api', 'search_ticker',
    'run_buyandhold_backtest', ' calculate_statistics','plot_buyandhold',
    'run_dca_backtest', 'plot_dca',
    'MACrossBacktester',
    'MomentumBacktester',
    'calculate_correlation_matrix', 'plot_correlation_matrix',
    'FGBacktest'  
]
