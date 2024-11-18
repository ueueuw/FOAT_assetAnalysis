import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import bt
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging
import numpy as np

class MomentumBacktester:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def _generate_momentum_signal(data, lookback=63):
        """모멘텀 시그널 생성"""
        momentum = data / data.shift(lookback) - 1
        signal = pd.DataFrame(0, index=data.index, columns=data.columns)
        
        for idx in momentum.index:
            row = momentum.loc[idx]
            if row.max() > 0:  # 양의 모멘텀이 있는 경우만
                signal.loc[idx, row.idxmax()] = 1
                    
        return signal
    
    class _MomentumStrategy(bt.Algo):
        """모멘텀 전략"""
        def __init__(self, lookback=63):
            self.lookback = lookback
                
        def __call__(self, target):
            data = target.universe
            signal = MomentumBacktester._generate_momentum_signal(data, self.lookback)
            weights = signal.iloc[-1]
            target.temp['weights'] = weights
            return True
    
    def fetch_data(self, tickers, start_date, end_date, lookback=63):
        """야후 파이낸스에서 데이터 가져오기"""
        extended_start_date = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=lookback * 2)).strftime("%Y-%m-%d")
        
        data = pd.DataFrame()
        for ticker in tickers:
            df = yf.download(ticker, start=extended_start_date, end=end_date, progress=False)['Adj Close']
            data[ticker] = df
            
            if data.isnull().values.any():
                data.fillna(method='ffill', inplace=True)
                if data.isnull().values.any():
                    data.fillna(method='bfill', inplace=True)
                if data.isnull().values.any():
                    data.dropna(inplace=True)
            
        return data
    
    def run_backtest(self, tickers, lookback, start_date, end_date):
        """모멘텀 전략 백테스트 실행"""
        strategy = bt.Strategy('Momentum',
                            [bt.algos.RunMonthly(),
                             bt.algos.SelectAll(),
                             self._MomentumStrategy(lookback),
                             bt.algos.Rebalance()])
        
        backtest = bt.Backtest(strategy, self.fetch_data(tickers, start_date, end_date, lookback))
        results = bt.run(backtest)
        return results
    
    def plot_results(self, results, data, start_date, end_date, title, tickers, image_path):
        """백테스트 결과 시각화"""
        daily_returns = results.prices.pct_change()
        
        end_date_dt = pd.to_datetime(end_date)
        start_date_dt = pd.to_datetime(start_date)
        
        if results.prices.index.tz is None:
            end_date_dt = end_date_dt.tz_localize('UTC')
            start_date_dt = start_date_dt.tz_localize('UTC')
        else:
            end_date_dt = end_date_dt.tz_localize('UTC').tz_convert(results.prices.index.tz)
            start_date_dt = start_date_dt.tz_localize('UTC').tz_convert(results.prices.index.tz)
        
        historical_returns = daily_returns[daily_returns.index <= end_date_dt]
        std_dev = historical_returns.std()
        
        actual_performance = results.prices.loc[start_date_dt:end_date_dt]
        initial_value = actual_performance.iloc[0]
        scaling_factor = 100 / initial_value
        scaled_performance = actual_performance * scaling_factor
        
        last_value = scaled_performance.iloc[-1]
        
        future_dates = pd.date_range(start=end_date_dt, periods=4, freq='B')[1:]
        upper_bound = last_value * (1 + 2 * std_dev)
        lower_bound = last_value * (1 - 2 * std_dev)
        
        plt.figure(figsize=(14, 7))
        scaled_performance.plot(color='blue', label='Actual Performance')
        
        plt.plot([end_date_dt, future_dates[-1]], [last_value, upper_bound], 
                 'r--', label='±2σ Forecast Range')
        plt.plot([end_date_dt, future_dates[-1]], [last_value, lower_bound], 
                 'r--')
        
        signals = self._generate_momentum_signal(data, lookback=63)
        signals = signals.loc[start_date_dt:end_date_dt]
        
        markers = ['^', 's', 'D', 'P', '*', 'X', 'o']
        marker_dict = {ticker: markers[i % len(markers)] for i, ticker in enumerate(tickers)}
        
        for ticker in tickers:
            buy_dates = signals[signals[ticker] == 1].index
            plt.plot(buy_dates, scaled_performance.loc[buy_dates], 
                     marker_dict[ticker], markersize=6, 
                     label=f'Buy Signal: {ticker}', linestyle='None')
        
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.grid(True)
        plt.legend()
        plt.savefig(image_path, bbox_inches='tight')
        plt.close()
        
        performance = results.display()
        return performance
    
    def calculate_statistics(self, results):
        """백테스트 결과의 주요 통계 계산"""
        mu = results.stats.loc['yearly_mean', 'Momentum']
        vol = results.stats.loc['daily_vol', 'Momentum']
        
        total_days = len(results.prices.index)
        num_years = total_days / 252  # trading days per year
        
        se = vol / np.sqrt(num_years)
        expected_return = mu
        
        return {
            'mu': mu,
            'se': se,
            'expected_return': expected_return,
            'volatility': vol,
            'sharpe_ratio': results.stats.loc['yearly_sharpe', 'Momentum'],
            'max_drawdown': results.stats.loc['max_drawdown', 'Momentum'],
            'total_return': results.stats.loc['total_return', 'Momentum'],
            'cagr': results.stats.loc['cagr', 'Momentum']
        }