# models/backtesting/test_Backtesting_BuyandHold.py

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import bt
import pandas as pd
import yfinance as yf
import logging
import numpy as np
from datetime import datetime, timedelta

class BuyAndHoldStrategy(bt.Algo):
    """
    매수 후 보유(Buy and Hold) 전략
    """
    def __init__(self, weights):
        """
        Parameters:
        weights (dict): 각 자산별 목표 비중 (예: {'AAPL': 0.6, 'MSFT': 0.4})
        """
        self.weights = weights
        self._has_traded = False
        
    def __call__(self, target):
        # 첫 거래일 때만 매수하고 이후에는 보유
        if not self._has_traded:
            target.temp['weights'] = pd.Series(self.weights)
            self._has_traded = True
            return True
            
        return False

def fetch_data(tickers, start_date, end_date):
    """
    야후 파이낸스에서 데이터 가져오기
    """
    data = pd.DataFrame()
    for ticker in tickers:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)['Adj Close']
        data[ticker] = df
        
        # 결측치 확인
        if data.isnull().values.any():
            logging.warning("데이터에 NaN 값이 포함되어 있습니다. NaN 값을 전방 채움으로 처리합니다.")
            data.fillna(method='ffill', inplace=True)
            if data.isnull().values.any():
                logging.warning("전방 채움 후에도 NaN 값이 존재합니다. 후방 채움으로 추가 처리합니다.")
                data.fillna(method='bfill', inplace=True)
            if data.isnull().values.any():
                logging.error("데이터 전처리 후에도 NaN 값이 존재합니다. 해당 날짜의 데이터를 제거합니다.")
                data.dropna(inplace=True)
        else:
            logging.info("데이터에 NaN 값이 없습니다.")
        
    return data

def run_buyandhold_backtest(tickers, weights, start_date, end_date):
    """
    매수 후 보유 전략 백테스트 실행
    """
    strategy = bt.Strategy('BuyAndHold',
                           [BuyAndHoldStrategy(weights),
                            bt.algos.Rebalance()])
    
    backtest = bt.Backtest(strategy, fetch_data(tickers, start_date, end_date))
    results = bt.run(backtest)
    return results

def plot_results_with_forecast(results, data, end_date, title, image_path):
    """
    백테스트 결과 시각화 (예측 범위 포함)
    """
    # 일별 수익률 계산
    daily_returns = results.prices.pct_change()
    
    # end_date까지의 수익률 데이터로 표준편차 계산
    end_date_dt = pd.to_datetime(end_date).tz_localize('UTC')  # 타임존 추가
    historical_returns = daily_returns[daily_returns.index <= end_date_dt]
    std_dev = historical_returns.std()
    
    # 마지막 포트폴리오 가치
    last_value = results.prices[results.prices.index <= end_date_dt].iloc[-1]
    
    # 예측 범위 생성
    future_dates = pd.date_range(start=end_date_dt, periods=8, freq='B')[1:]  # 5 영업일
    upper_bound = last_value * (1 + 2 * std_dev)
    lower_bound = last_value * (1 - 2 * std_dev)
    
    # 결과 플로팅
    plt.figure(figsize=(12, 6))
    
    # 실제 수익률 플로팅
    results.prices[results.prices.index <= end_date_dt].plot(color='blue', label='Actual Performance')
    
    # 예측 범위 플로팅
    plt.plot([end_date_dt, future_dates[-1]], [last_value, upper_bound], 
             'r--', label='±2σ Forecast Range')
    plt.plot([end_date_dt, future_dates[-1]], [last_value, lower_bound], 
             'r--')
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value')
    plt.grid(True)
    plt.legend()
    plt.savefig(image_path, bbox_inches='tight')  # 서버에 저장
    plt.close()
    
    # 주요 성과 지표 출력
    performance = results.display()
    return performance
