import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import bt
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging
import numpy as np

logger = logging.getLogger(__name__)

def MA_Signal(data, short_ma=20, long_ma=100):
    """
    이동평균선 교차 시그널 생성
    """
    sma = data.rolling(short_ma).mean()
    lma = data.rolling(long_ma).mean()
    
    signal = pd.DataFrame(0, index=data.index, columns=data.columns)
    
    prev_sma = sma.shift(1)
    prev_lma = lma.shift(1)
    
    buy_signals = (sma > lma) & (prev_sma <= prev_lma)
    sell_signals = (sma < lma) & (prev_sma >= prev_lma)
    
    signal[buy_signals] = 1
    signal[sell_signals] = -1
    
    return signal

class MACrossStrategy(bt.Algo):
    """
    이동평균선 교차 전략
    """
    def __init__(self, short_ma=20, long_ma=100):
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.positions = {}
        
    def __call__(self, target):
        current_date = target.now
        data = target.universe
        
        signal = MA_Signal(data, self.short_ma, self.long_ma)
        
        try:
            latest_signal = signal.loc[current_date]
        except KeyError:
            return False
        
        weights = pd.Series(0, index=latest_signal.index)
        
        for asset in latest_signal.index:
            sig = latest_signal[asset]
            if asset not in self.positions:
                self.positions[asset] = 0
                
            if sig == 1:
                self.positions[asset] = 1
            elif sig == -1:
                self.positions[asset] = 0
                
            weights[asset] = self.positions[asset]
        
        total_positions = weights.sum()
        if total_positions != 0:
            weights = weights / total_positions
        else:
            weights = pd.Series(0, index=weights.index)
        
        target.temp['weights'] = weights
        
        return True

class MACrossBacktester:
    """
    이동평균선 교차 전략 백테스터
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def fetch_data(self, tickers, start_date, end_date, long_ma=100):
        """
        야후 파이낸스에서 데이터 가져오기
        """
        extended_start_date = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=long_ma*2)).strftime("%Y-%m-%d")
        
        data = pd.DataFrame()
        for ticker in tickers:
            df = yf.download(ticker, start=extended_start_date, end=end_date, progress=False)['Adj Close']
            data[ticker] = df
            
            if data.isnull().values.any():
                self.logger.warning(f"{ticker}: NaN 값이 발견되어 전처리를 수행합니다.")
                data.fillna(method='ffill', inplace=True)
                if data.isnull().values.any():
                    data.fillna(method='bfill', inplace=True)
                if data.isnull().values.any():
                    data.dropna(inplace=True)
            
        return data

    def run_backtest(self, tickers, short_ma, long_ma, start_date, end_date):
        """
        백테스트 실행
        """
        strategy = bt.Strategy('MA_Crossover', 
                             [bt.algos.RunDaily(),
                              bt.algos.SelectAll(),
                              MACrossStrategy(short_ma, long_ma),
                              bt.algos.Rebalance()])
        
        data = self.fetch_data(tickers, start_date, end_date, long_ma)
        backtest = bt.Backtest(strategy, data)
        results = bt.run(backtest)
        
        return results, data

    def plot_results(self, results, data, start_date, end_date, title, image_path):
        """
        백테스트 결과 시각화
        """
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
        
        last_value = results.prices[results.prices.index <= end_date_dt].iloc[-1]
        
        future_dates = pd.date_range(start=end_date_dt, periods=4, freq='B')[1:]
        upper_bound = last_value * (1 + 2 * std_dev)
        lower_bound = last_value * (1 - 2 * std_dev)
        
        plt.figure(figsize=(14, 7))
        
        actual_performance = results.prices.loc[start_date_dt:end_date_dt]
        actual_performance.plot(color='blue', label='Actual Performance')
        
        plt.plot([end_date_dt, future_dates[-1]], [last_value, upper_bound], 
                 'r--', label='±2σ Forecast Range')
        plt.plot([end_date_dt, future_dates[-1]], [last_value, lower_bound], 
                 'r--')
        
        signals = MA_Signal(data, short_ma=20, long_ma=100)
        signals = signals.loc[start_date_dt:end_date_dt]
        
        buy_dates = signals[signals == 1].dropna(how='all').index
        sell_dates = signals[signals == -1].dropna(how='all').index
        
        plt.plot(buy_dates, actual_performance.loc[buy_dates], '^', 
                markersize=10, color='green', label='Buy Signal')
        plt.plot(sell_dates, actual_performance.loc[sell_dates], 'v', 
                markersize=10, color='red', label='Sell Signal')
        
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.grid(True)
        plt.legend()
        plt.savefig(image_path, bbox_inches='tight')
        plt.close()
        
        performance = results.display()
        return performance

    def get_performance_metrics(self, results):
        """
        성능 지표 계산
        수정된 버전: 연간 수익률(mu)과 표준오차(SE) 계산
        """
        try:
            # 연간 평균 수익률 (mu) 계산 - yearly_mean 사용
            mu = results.stats.loc['yearly_mean', 'MA_Crossover']
            
            # 일별 변동성을 연간화하여 계산
            daily_vol = results.stats.loc['daily_vol', 'MA_Crossover']
            vol = daily_vol * np.sqrt(252)  # 252 trading days per year
            
            # 관측치 수 계산
            num_obs = len(results.prices.index)
            
            # 표준오차 계산
            se = vol / np.sqrt(num_obs)
            
            # 예상 수익률은 연간 평균 수익률과 동일
            expected_return = mu
            
            metrics = {
                'mu': mu,
                'vol': vol,
                'se': se,
                'expected_return': expected_return,
                # 추가 메트릭스
                'sharpe_ratio': results.stats.loc['daily_sharpe', 'MA_Crossover'],
                'max_drawdown': results.stats.loc['max_drawdown', 'MA_Crossover'],
                'cagr': results.stats.loc['cagr', 'MA_Crossover']
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"성능 지표 계산 중 오류 발생: {e}", exc_info=True)
            return None
        