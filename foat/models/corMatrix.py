# models/corMatrix.py

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# (2) 자산 간의 Correlation Matrix 조회 함수
def calculate_correlation_matrix(ticker_list, period):
    stock_data = pd.DataFrame()

    # CSV 파일 읽기
    csv_data = pd.read_csv('data/data__NationwideAndSeoul.csv', parse_dates=['Date'])
    csv_data.set_index('Date', inplace=True)
    
    for ticker in ticker_list:
        if ticker == 'entireAPT_Korea':
            # Nationwide 열을 사용
            if 'Nationwide' in csv_data.columns:
                stock_data[ticker] = csv_data['Nationwide']
            else:
                raise ValueError('Nationwide 열이 CSV 파일에 존재하지 않습니다.')
        elif ticker == 'SeoulAPT_Korea':
            # Seoul 열을 사용
            if 'Seoul' in csv_data.columns:
                stock_data[ticker] = csv_data['Seoul']
            else:
                raise ValueError('Seoul 열이 CSV 파일에 존재하지 않습니다.')
        else:
            # yfinance에서 데이터 다운로드
            data = yf.download(ticker, period=period)['Adj Close']
            if data.empty:
                raise ValueError(f'{ticker}에 대한 데이터를 찾을 수 없습니다.')
            # 주간 수익률 계산 (매주 월요일 기준)
            weekly_returns = data.resample('W-MON').ffill().pct_change().dropna()
            stock_data[ticker] = weekly_returns

    if stock_data.empty:
        raise ValueError('종목 데이터가 비어 있습니다.')

    # 모든 자산의 수익률 데이터 결합 (날짜 기준으로)
    combined_data = stock_data.dropna()

    if combined_data.empty:
        raise ValueError('결합된 자산의 수익률 데이터가 비어 있습니다.')

    # 수익률로 상관계수 행렬 계산
    return_matrix = combined_data.corr()

    # 상삼각행렬 추출 (대각선 제외)
    mask = np.triu(np.ones(return_matrix.shape), k=1).astype(bool)
    upper_tri_matrix = return_matrix.where(mask)

    # 상관계수 행렬을 딕셔너리로 변환
    correlation_dict = upper_tri_matrix.to_dict()

    return correlation_dict

# (Optional) 상관관계 행렬 시각화 함수 (웹에서는 필요 없을 수 있음)
def plot_correlation_matrix(correlation_dict, ticker_list, period):
    correlation_df = pd.DataFrame(correlation_dict)
    mask = np.triu(np.ones(correlation_df.shape), k=1).astype(bool)
    upper_tri_matrix = correlation_df.where(mask)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    cax = ax.matshow(upper_tri_matrix, cmap='RdYlGn', vmin=-1, vmax=1)
    for (i, j), val in np.ndenumerate(upper_tri_matrix.values):
        if not np.isnan(val):
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color='black')
    ax.set_xticks(range(len(ticker_list)))
    ax.set_xticklabels(ticker_list, rotation=90)
    ax.set_yticks(range(len(ticker_list)))
    ax.set_yticklabels(ticker_list)
    ax.set_title(f'{period.capitalize()} Upper Triangular Correlation Matrix', pad=20)
    plt.show()
