# models/model.py

import yfinance as yf
import requests
import pandas as pd
import time

# (1) 주식 가격 조회 함수
def fetch_stock_prices(stock_symbols):
    """
    주어진 주식 심볼의 가격을 yfinance에서 가져와서 USD로 환전하여 딕셔너리로 반환.
    stock_symbols: 가격을 가져올 주식/코인 심볼 리스트
    """
    stock_prices = {}
    exchange_rates = {}
    
    for symbol in stock_symbols:
        ticker = yf.Ticker(symbol)
        stock_info = ticker.history(period="1d")
        
        if not stock_info.empty:
            # 종가를 사용하여 가격을 설정
            close_price = stock_info['Close'].iloc[-1]
            
            # 종목의 통화 정보 가져오기
            info = ticker.info
            currency = info.get('currency', 'USD')
            
            if currency != 'USD':
                # 이미 조회한 통화인 경우 캐시된 환율 사용
                if currency in exchange_rates:
                    exchange_rate = exchange_rates[currency]
                else:
                    # 환율 티커 형식 (예: KRWUSD=X)
                    exchange_ticker = f"{currency}USD=X"
                    exchange_info = yf.Ticker(exchange_ticker).history(period="1d")
                    if not exchange_info.empty:
                        exchange_rate = exchange_info['Close'].iloc[-1]
                        exchange_rates[currency] = exchange_rate
                    else:
                        # 환율 정보를 가져올 수 없는 경우 기본값 1 사용
                        exchange_rate = 1
                        exchange_rates[currency] = exchange_rate
                
                # USD로 환전
                usd_price = close_price * exchange_rate
                stock_prices[symbol] = round(usd_price, 2)
            else:
                stock_prices[symbol] = round(close_price, 2)
        else:
            stock_prices[symbol] = 0  # 가격 정보를 찾을 수 없는 경우 0으로 설정
    
    return stock_prices

# (2) 현재 자산 설정 및 조회 함수
def set_asset(current_cash, stock_holdings):
    """
    current_cash: 현재 보유 현금 (현금 자산)
    stock_holdings: 각 주식/코인의 보유 수량 (ex. {'AAPL': 10, 'BTC-USD': 0.05})
    """
    # 보유한 주식/코인 리스트에서 가격 가져오기
    stock_symbols = list(stock_holdings.keys())
    stock_prices = fetch_stock_prices(stock_symbols)
    
    # 각 자산의 실제 가치를 계산하여 total_asset에 반영
    asset_values = {asset: quantity * stock_prices.get(asset, 0) for asset, quantity in stock_holdings.items()}
    asset_values['Cash'] = current_cash
    total_asset = sum(asset_values.values())
    
    # 비율 계산을 위해 각 자산의 가치를 리스트에 추가
    labels = list(asset_values.keys())
    sizes = list(asset_values.values())
    
    # 결과 반환
    response = {
        'current_cash': current_cash,
        'stock_holdings': stock_holdings,
        'stock_prices': stock_prices,
        'total_asset': round(total_asset, 2),
        'labels': labels,
        'sizes': sizes
    }
    return response

# (3) 목표 수익률 계산 함수
def calculate_required_return(current_asset, target_asset, years):
    """
    현재 자산, 목표 자산, 기간을 기반으로 연간 필요한 수익률을 계산합니다.
    """
    if current_asset <= 0 or target_asset <= 0 or years <= 0:
        return None
    return_rate = ((target_asset / current_asset) ** (1 / years)) - 1
    return return_rate * 100

def calculate_required_return_api(current_asset, target_asset, years):
    """
    API 호출을 위한 함수. calculate_required_return을 호출하고 결과 반환.
    """
    required_return = calculate_required_return(current_asset, target_asset, years)
    if required_return is None:
        return {'error': '잘못된 입력입니다.'}
    return {'required_return_per_year': round(required_return, 2)}

# (4) 검색 로직
def search_ticker(keyword, max_results=5, retries=3, backoff_factor=2):
    """
    종목 키워드를 입력받아 관련 티커를 검색하여 반환합니다.
    재시도 로직과 지연 시간을 포함하여 속도 제한을 피합니다.
    
    :param keyword: str, 검색할 종목 키워드
    :param max_results: int, 반환할 최대 결과 수
    :param retries: int, 최대 재시도 횟수
    :param backoff_factor: int/float, 재시도 시 지연 시간 배수
    :return: 리스트 of dict, 검색된 티커 정보 (Symbol, Name, Type, Exchange)
    """
    url = 'https://query2.finance.yahoo.com/v1/finance/search'
    params = {
        'q': keyword,
        'quotesCount': max_results,
        'newsCount': 0,
        'enableFuzzyQuery': True,
        'quotesQueryId': 'tss_match_phrase_suffix'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'quotes' not in data or not data['quotes']:
                print("검색 결과가 없습니다.")
                return []
            
            quotes = data['quotes']
            results = []
            for quote in quotes:
                symbol = quote.get('symbol', 'N/A')
                name = quote.get('shortname') or quote.get('longname') or 'N/A'
                type_ = quote.get('quoteType', 'N/A')
                exchange = quote.get('exchange', 'N/A')
                
                # 선물(FUTURE) 유형 제외
                if type_.upper() == 'FUTURE':
                    continue
                
                results.append({
                    'Symbol': symbol,
                    'Name': name,
                    'Type': type_,
                    'Exchange': exchange
                })
            
            return results
        
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 429:
                wait_time = backoff_factor ** attempt
                print(f"HTTP 429 오류 발생. {wait_time}초 후에 재시도합니다...")
                time.sleep(wait_time)
            else:
                print(f"HTTP 오류 발생: {http_err}")
                break
        except requests.exceptions.RequestException as req_err:
            print(f"요청 중 오류 발생: {req_err}")
            break
        except ValueError:
            print("응답을 JSON으로 파싱하는 중 오류 발생.")
            break
    
    print("최대 재시도 횟수를 초과했습니다.")
    return []
