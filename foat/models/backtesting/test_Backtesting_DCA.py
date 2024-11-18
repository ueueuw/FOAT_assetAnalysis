import bt
import pandas as pd
import yfinance as yf
import logging
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

class DCAStrategy(bt.Algo):
    """
    분할매수(Dollar Cost Averaging) 전략
    """
    def __init__(self, weights, period='M'):
        """
        Parameters:
        weights (dict): 각 자산별 목표 비중 (예: {'AAPL': 0.6, 'MSFT': 0.4})
        period (str): 투자 주기 ('M': 월별, 'W': 주별, 'D': 일별)
        """
        self.weights = weights
        self.period = period
        self._last_trade_date = None
        
    def __call__(self, target):
        current_date = target.now
        
        if self._last_trade_date is None:
            should_trade = True
        else:
            if self.period == 'M':
                should_trade = current_date.month != self._last_trade_date.month
            elif self.period == 'W':
                should_trade = current_date.isocalendar()[1] != self._last_trade_date.isocalendar()[1]
            elif self.period == 'D':
                should_trade = current_date.date() != self._last_trade_date.date()
            else:
                should_trade = False
        
        if should_trade:
            target.temp['weights'] = pd.Series(self.weights)
            self._last_trade_date = current_date
            return True
            
        return False

def fetch_data(tickers, start_date, end_date):
    """야후 파이낸스에서 데이터 가져오기"""
    data = pd.DataFrame()
    for ticker in tickers:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)['Adj Close']
        data[ticker] = df
        
        if data.isnull().values.any():
            logging.warning("NaN 값이 포함되어 있어 전방 채움으로 처리합니다.")
            data.fillna(method='ffill', inplace=True)
            if data.isnull().values.any():
                data.fillna(method='bfill', inplace=True)
            if data.isnull().values.any():
                data.dropna(inplace=True)
                
    return data

def run_dca_backtest(tickers, weights, period, start_date, end_date):
    """분할매수 전략 백테스트 실행"""
    strategy = bt.Strategy('DCA',
                         [DCAStrategy(weights, period),
                          bt.algos.Rebalance()])
    
    backtest = bt.Backtest(strategy, fetch_data(tickers, start_date, end_date))
    results = bt.run(backtest)
    return results

def plot_results_with_forecast(results, end_date, title, image_path):
    """백테스트 결과 시각화 (예측 범위 포함)"""
    daily_returns = results.prices.pct_change()
    end_date_dt = pd.to_datetime(end_date).tz_localize('UTC')
    historical_returns = daily_returns[daily_returns.index <= end_date_dt]
    std_dev = historical_returns.std()
    last_value = results.prices[results.prices.index <= end_date_dt].iloc[-1]
    
    future_dates = pd.date_range(start=end_date_dt, periods=8, freq='B')[1:]
    upper_bound = last_value * (1 + 2 * std_dev)
    lower_bound = last_value * (1 - 2 * std_dev)
    
    plt.figure(figsize=(12, 6))
    results.prices[results.prices.index <= end_date_dt].plot(color='blue', 
                                                           label='Actual Performance')
    
    plt.plot([end_date_dt, future_dates[-1]], [last_value, upper_bound], 
             'r--', label='±2σ Forecast Range')
    plt.plot([end_date_dt, future_dates[-1]], [last_value, lower_bound], 
             'r--')
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value')
    plt.grid(True)
    plt.legend()
    plt.savefig(image_path, bbox_inches='tight')
    plt.close()
    
    return {
        'daily_returns': daily_returns,
        'std_dev': std_dev,
        'last_value': last_value
    }

def calculate_statistics(results, daily_returns):
    """주요 통계 계산"""
    if 'daily_mean' in results.stats.index and 'DCA' in results.stats.columns:
        mu = results.stats.loc['yearly_mean', 'DCA']
    else:
        mu = daily_returns.mean()
    
    if 'daily_vol' in results.stats.index and 'DCA' in results.stats.columns:
        vol = results.stats.loc['daily_vol', 'DCA']
    else:
        vol = daily_returns.std()

    num_obs = len(results.prices.index)
    se = vol / np.sqrt(num_obs)
    expected_return = mu
    
    return {
        'mu': mu,
        'vol': vol,
        'se': se,
        'expected_return': expected_return
    }

