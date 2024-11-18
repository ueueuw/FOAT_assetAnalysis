# models/backtesting/testFGI.py

import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

class FGBacktest:
    def __init__(self, fg_data_path, buy_threshold=25, sell_threshold=75):
        # Load and process Fear & Greed data
        self.fg_data = pd.read_csv(fg_data_path)
        self.fg_data['Date'] = pd.to_datetime(self.fg_data['Date']).dt.tz_localize('UTC')
        self.fg_data.set_index('Date', inplace=True)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.results = None
        
    def prepare_data(self, start_date, end_date):
        # Convert dates to UTC timezone
        start_date = pd.to_datetime(start_date).tz_localize('UTC')
        end_date = pd.to_datetime(end_date).tz_localize('UTC')
        
        # Get SPY data first
        spy_data = yf.download('SPY', start=start_date, end=end_date)['Close']
        
        # Convert spy_data index to UTC timezone if not already
        if spy_data.index.tz is None:
            spy_data.index = spy_data.index.tz_localize('UTC')
        
        spy_data = pd.DataFrame(spy_data)
        spy_data.columns = ['SPY']
        
        # Filter and align Fear & Greed data
        fg_filtered = self.fg_data[
            (self.fg_data.index >= start_date) & 
            (self.fg_data.index <= end_date)
        ].copy()
        
        # Merge the data
        data = pd.merge(
            spy_data,
            fg_filtered,
            left_index=True,
            right_index=True,
            how='left'
        )
        
        # Forward fill any missing Fear & Greed values
        data['Fear Greed'] = data['Fear Greed'].ffill()
        
        # Drop any remaining NaN values
        data = data.dropna()
        
        if len(data) == 0:
            raise ValueError("No data available for the specified date range")
        
        # Generate position signals
        data['Signal'] = 0
        data.loc[data['Fear Greed'] <= self.buy_threshold, 'Signal'] = 1  # Buy signal
        data.loc[data['Fear Greed'] >= self.sell_threshold, 'Signal'] = -1  # Sell signal
    
        # Initialize positions
        data['Position'] = 0
    
        # Carry forward positions
        data['Position'] = data['Signal'].replace(to_replace=0, method='ffill').fillna(0)
    
        # Set position to 0 where sell signal is generated
        data.loc[data['Signal'] == -1, 'Position'] = 0
    
        # Shift positions by 1 day to avoid look-ahead bias
        data['Position'] = data['Position'].shift(1).fillna(0)
    
        return data
    
    def calculate_returns(self, data):
        # Calculate daily returns
        data['SPY_Returns'] = data['SPY'].pct_change()
        
        # Calculate strategy returns (only when we hold position)
        data['Strategy_Returns'] = data['SPY_Returns'] * data['Position']
        
        # Replace any inf or -inf values with 0
        data['Strategy_Returns'] = data['Strategy_Returns'].replace([np.inf, -np.inf], 0)
        
        # Calculate cumulative returns starting from 1
        data['Cum_Market_Returns'] = (1 + data['SPY_Returns'].fillna(0)).cumprod()
        data['Cum_Strategy_Returns'] = (1 + data['Strategy_Returns'].fillna(0)).cumprod()
        
        # Calculate monetary values (assuming $10,000 initial investment)
        initial_investment = 10000
        data['Market_Value'] = initial_investment * data['Cum_Market_Returns']
        data['Strategy_Value'] = initial_investment * data['Cum_Strategy_Returns']
        
        return data
    
    def calculate_metrics(self, data):
        # Ensure we have sufficient data
        if len(data) < 2:
            raise ValueError("Insufficient data for calculating metrics")
            
        # Calculate various performance metrics
        strategy_returns = data['Strategy_Returns'].fillna(0)
        market_returns = data['SPY_Returns'].fillna(0)
        
        # Avoid division by zero
        strategy_std = strategy_returns.std()
        market_std = market_returns.std()
        
        metrics = {
            'Total Return (Strategy)': (data['Strategy_Value'].iloc[-1] / data['Strategy_Value'].iloc[0] - 1) * 100,
            'Total Return (Market)': (data['Market_Value'].iloc[-1] / data['Market_Value'].iloc[0] - 1) * 100,
            'Annual Return (Strategy)': (((data['Strategy_Value'].iloc[-1] / data['Strategy_Value'].iloc[0]) ** (252/len(data))) - 1) * 100,
            'Annual Return (Market)': (((data['Market_Value'].iloc[-1] / data['Market_Value'].iloc[0]) ** (252/len(data))) - 1) * 100,
            'Volatility (Strategy)': strategy_std * np.sqrt(252) * 100,
            'Volatility (Market)': market_std * np.sqrt(252) * 100,            
        }
        
        return metrics
    
    def plot_results(self, data, save_path):
        # Convert timezone-aware index to timezone-naive for plotting
        data_plot = data.copy()
        data_plot.index = data_plot.index.tz_localize(None)
        
        # Create figure and axis
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), gridspec_kw={'height_ratios': [2, 1]})
        
        # Plot portfolio values
        ax1.plot(data_plot.index, data_plot['Market_Value'], label='Buy & Hold', alpha=0.7)
        ax1.plot(data_plot.index, data_plot['Strategy_Value'], label='F&G Strategy', alpha=0.7)
        ax1.set_title('Portfolio Value Over Time ($10,000 Initial Investment)')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.grid(True)
        ax1.legend()
        
        # Plot Fear & Greed Index with buy/sell thresholds
        ax2.plot(data_plot.index, data_plot['Fear Greed'], label='Fear & Greed Index', color='purple', alpha=0.7)
        ax2.axhline(y=self.buy_threshold, color='g', linestyle='--', label=f'Buy Threshold ({self.buy_threshold})')
        ax2.axhline(y=self.sell_threshold, color='r', linestyle='--', label=f'Sell Threshold ({self.sell_threshold})')
        ax2.set_title('Fear & Greed Index')
        ax2.set_ylabel('Index Value')
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        
    def run_backtest(self, buy_threshold, sell_threshold, start_date, end_date):
        try:
            # Validate date range
            min_date = '2011-01-03'
            max_date = '2022-12-30'
            if not (min_date <= start_date <= max_date):
                raise ValueError(f"시작 날짜는 {min_date}부터 {max_date} 사이여야 합니다.")
            if not (min_date <= end_date <= max_date):
                raise ValueError(f"종료 날짜는 {min_date}부터 {max_date} 사이여야 합니다.")
            if start_date > end_date:
                raise ValueError("시작 날짜는 종료 날짜보다 이전이어야 합니다.")
            
            self.buy_threshold = buy_threshold
            self.sell_threshold = sell_threshold
            
            # Prepare data
            print("Preparing data...")
            data = self.prepare_data(start_date, end_date)
            
            # Check if we have enough data
            if len(data) < 2:
                raise ValueError("Insufficient data for backtesting")
            
            print(f"Processing {len(data)} data points...")
            
            # Calculate returns and metrics
            data = self.calculate_returns(data)
            metrics = self.calculate_metrics(data)
            
            # Store results
            self.results = {
                'data': data,
                'metrics': metrics
            }
            
            # Print metrics
            print("\n=== Performance Metrics ===")
            for metric, value in metrics.items():
                print(f"{metric}: {value:.2f}")
                
            # Plot results
            plot_filename = f"fgi_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            save_path = os.path.join('static', 'plots', plot_filename)
            self.plot_results(data, save_path)
            
            return {
                'metrics': metrics,
                'plot_filename': plot_filename
            }
            
        except Exception as e:
            print(f"Error during backtesting: {str(e)}")
            raise
