# controller.py

from flask import render_template, request, jsonify
from datetime import datetime
import os, logging, numpy as np
import matplotlib.pyplot as plt
from models import (
    set_asset, 
    calculate_required_return_api, 
    search_ticker, 
    fetch_stock_prices,
    run_buyandhold_backtest, 
    plot_buyandhold,
    run_dca_backtest, 
    plot_dca,
    calculate_statistics,
    MACrossBacktester,
    MomentumBacktester,
    FGBacktest,
    calculate_correlation_matrix,
    plot_correlation_matrix  
)

# 로거 설정
logger = logging.getLogger(__name__)

# Helper 함수
def is_close(a, b, tol):
    return abs(a - b) < tol

def register_routes(app):
    # 플롯 저장 디렉토리 경로
    PLOT_DIR = os.path.join('static', 'plots')
    
    # 기본 라우트
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/backtesting')
    def backtesting():
        return render_template('backtesting.html')

    @app.route('/analysis')
    def analysis():
        return render_template('analysis.html')

    @app.route('/lab')
    def lab():
        return render_template('lab.html')
    
    # (1) 자산 설정 및 조회 API
    @app.route('/api/set_asset', methods=['POST'])
    def api_set_asset():
        data = request.get_json()
        current_cash = data.get('current_cash', 0)
        stock_holdings = data.get('stock_holdings', {})
        
        if current_cash < 0:
            return jsonify({'error': '현금 자산은 0 이상이어야 합니다.'}), 400
        
        # 자산 설정 및 조회
        asset_info = set_asset(current_cash, stock_holdings)
        
        return jsonify(asset_info), 200

    # (2) 목표 수익률 계산 API
    @app.route('/api/calculate_required_return', methods=['POST'])
    def api_calculate_required_return():
        data = request.get_json()
        current_asset = data.get('current_asset', 0)
        target_asset = data.get('target_asset', 0)
        years = data.get('years', 1)
        
        if current_asset <= 0 or target_asset <= 0 or years <= 0:
            return jsonify({'error': '현재 자산, 목표 자산, 기간은 0보다 커야 합니다.'}), 400
        
        required_return = calculate_required_return_api(current_asset, target_asset, years)
        
        if 'error' in required_return:
            return jsonify(required_return), 400
        
        return jsonify(required_return), 200

    # (3) 티커 검색 API
    @app.route('/api/search_ticker', methods=['GET'])
    def api_search_ticker():
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({'error': '키워드를 입력해주세요.'}), 400
        
        try:
            # model.py의 search_ticker 함수 호출
            results = search_ticker(keyword, max_results=5)  # 최대 5개 결과 반환
            # 필요한 필드만 추출하여 반환 (Symbol, Name, Exchange 포함)
            formatted_results = [{'Symbol': res['Symbol'], 'Name': res['Name'], 'Exchange': res['Exchange']} for res in results]
            return jsonify({'results': formatted_results}), 200
        except Exception as e:
            logger.error(f"티커 검색 오류: {e}")
            return jsonify({'error': '티커 검색 중 오류가 발생했습니다.'}), 500

    # (4) 종목 가격 조회 API
    @app.route('/api/get_stock_price', methods=['GET'])
    def get_stock_price():
        symbol = request.args.get('symbol', '').upper()
        if not symbol:
            return jsonify({'error': '종목 티커가 필요합니다.'}), 400
        try:
            stock_prices = fetch_stock_prices([symbol])
            price = stock_prices.get(symbol, 0)
            return jsonify({'symbol': symbol, 'price': price}), 200
        except Exception as e:
            logger.error(f"주식 가격 조회 오류: {e}")
            return jsonify({'error': '주식 가격을 가져오는 중 오류가 발생했습니다.'}), 500

    # (5) 상관관계 매트릭스 계산 API 수정
    @app.route('/api/calculate_correlation', methods=['POST'])
    def api_calculate_correlation():
        data = request.get_json()
        tickers = data.get('tickers', [])
        period = data.get('period', '1y')  # 기본 기간 설정

        # 유효성 검증
        valid_periods = ['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        if period not in valid_periods:
            return jsonify({'error': '유효하지 않은 기간이 선택되었습니다.'}), 400

        # 전체 종목 리스트 중복 제거
        allTickers = list(dict.fromkeys(tickers))

        if not allTickers:
            return jsonify({'error': '종목 목록이 비어 있습니다.'}), 400

        try:
            # 상관관계 계산
            correlation_dict = calculate_correlation_matrix(allTickers, period)
            
            # 상관관계 매트릭스 플롯 생성
            plot_correlation_matrix(correlation_dict, allTickers, period)
            
            # 고유한 파일명 생성 (예: corr_matrix_20241115_161516.png)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"corr_matrix_{timestamp}.png"
            image_path = os.path.join(PLOT_DIR, image_filename)
            
            # 현재 Figure를 이미지 파일로 저장
            plt.savefig(image_path, bbox_inches='tight')
            plt.close()
            
            # 이미지 URL 생성
            image_url = f"/static/plots/{image_filename}"
            
            return jsonify({'image_url': image_url}), 200
        except Exception as e:
            logger.error(f"상관관계 매트릭스 계산 오류: {e}")
            return jsonify({'error': str(e)}), 500

    # (6) FGI 백테스팅 API 수정
    @app.route('/api/backtest_fgi', methods=['POST'])
    def api_backtest_fgi():
        data = request.get_json()
        buy_threshold = data.get('buy_threshold')
        sell_threshold = data.get('sell_threshold')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 입력 검증
        if buy_threshold is None or sell_threshold is None or not start_date or not end_date:
            return jsonify({'error': '모든 입력값을 제공해야 합니다.'}), 400
        
        try:
            # 날짜 검증 (2011-01-03부터 2022-12-30까지)
            min_date = '2011-01-03'
            max_date = '2022-12-30'
            if not (min_date <= start_date <= max_date):
                return jsonify({'error': f"시작 날짜는 {min_date}부터 {max_date} 사이여야 합니다."}), 400
            if not (min_date <= end_date <= max_date):
                return jsonify({'error': f"종료 날짜는 {min_date}부터 {max_date} 사이여야 합니다."}), 400
            if start_date > end_date:
                return jsonify({'error': '시작 날짜는 종료 날짜보다 이전이어야 합니다.'}), 400
            
            # FGBacktest 클래스 인스턴스화
            fg_data_path = os.path.join('data', 'data_FGInSPY.csv')
            backtest = FGBacktest(
                fg_data_path=fg_data_path, 
                buy_threshold=buy_threshold, 
                sell_threshold=sell_threshold
            )
            
            # 백테스트 실행
            results = backtest.run_backtest(buy_threshold, sell_threshold, start_date, end_date)
            
            # 결과 반환
            return jsonify({
                'metrics': results['metrics'],
                'plot_url': f"/static/plots/{results['plot_filename']}"
            }), 200
        except Exception as e:
            logger.error(f"FGI 백테스팅 오류: {e}")
            return jsonify({'error': str(e)}), 500

    # (7) 매수&보유 전략 백테스팅 API 수정
    @app.route('/api/backtest_buyandhold', methods=['POST'])
    def api_backtest_buyandhold():
        data = request.get_json()
        tickers = data.get('tickers', [])
        weights = data.get('weights', {})
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 입력 검증
        if not tickers or not weights or not start_date or not end_date:
            return jsonify({'error': '모든 입력값을 제공해야 합니다.'}), 400
        
        # 비중의 합이 1인지 확인
        total_weight = sum(weights.values())
        if not is_close(total_weight, 1.0, 0.01):
            return jsonify({'error': '자산의 비중 합이 1에 가까워야 합니다.'}), 400
        
        try:
            # 파일명 생성 (예: buyandhold_20241115_161516.png)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"buyandhold_{timestamp}.png"
            image_path = os.path.join(PLOT_DIR, image_filename)
            
            # 백테스트 실행
            results = run_buyandhold_backtest(tickers, weights, start_date, end_date)

            # SPY 백테스트 실행
            spy_results = run_buyandhold_backtest(['SPY'], {'SPY': 1.0}, start_date, end_date)
            
            # 백테스트 결과 플롯 생성 및 이미지 저장
            plot_buyandhold(results, data=None, end_date=end_date, title='Buy and Hold Strategy with Forecast Range', image_path=image_path)

            # 비교 데이터 생성
            comparison_data = {
                'total_return': {
                    'Market (SPY)': spy_results.stats.loc['total_return', 'BuyAndHold'],
                    'Strategy': results.stats.loc['total_return', 'BuyAndHold']
                },
                'yearly_mean': {
                    'Market (SPY)': spy_results.stats.loc['yearly_mean', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_mean', 'BuyAndHold']
                },
                'yearly_vol': {
                    'Market (SPY)': spy_results.stats.loc['yearly_vol', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_vol', 'BuyAndHold']
                }
            }
            
            return jsonify({
                'plot_url': f"/static/plots/{image_filename}",
                'comparison_data': comparison_data
            }), 200
        
        except Exception as e:
            logger.error(f"Buy and Hold 백테스팅 오류: {e}")
            return jsonify({'error': '백테스팅 수행 중 오류가 발생했습니다.'}), 500
        
    # (8) DCA 전략 백테스팅 API 수정
    @app.route('/api/backtest_dca', methods=['POST'])
    def api_backtest_dca():
        data = request.get_json()
        tickers = data.get('tickers', [])
        weights = data.get('weights', {})
        period = data.get('period')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 입력 검증
        if not tickers or not weights or not period or not start_date or not end_date:
            return jsonify({'error': '모든 입력값을 제공해야 합니다.'}), 400
        
        total_weight = sum(weights.values())
        if not is_close(total_weight, 1.0, 0.01):
            return jsonify({'error': '자산의 비중 합이 1에 가까워야 합니다.'}), 400
        
        if period not in ['D', 'W', 'M']:
            return jsonify({'error': '투자 빈도는 "D", "W", "M" 중 하나여야 합니다.'}), 400
        
        try:
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"dca_{timestamp}.png"
            image_path = os.path.join(PLOT_DIR, image_filename)

            # 전략 백테스트 실행
            results = run_dca_backtest(tickers, weights, period, start_date, end_date)
            
            # SPY 백테스트 실행
            spy_results = run_buyandhold_backtest(['SPY'], {'SPY': 1.0}, start_date, end_date)
            
            # 결과 시각화
            plot_dca(results, end_date, 'Dollar Cost Averaging (DCA) Strategy with Forecast Range', image_path)
            
            # 비교 데이터 생성
            comparison_data = {
                'total_return': {
                    'Market (SPY)': spy_results.stats.loc['total_return', 'BuyAndHold'],
                    'Strategy': results.stats.loc['total_return', 'DCA']
                },
                'yearly_mean': {
                    'Market (SPY)': spy_results.stats.loc['yearly_mean', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_mean', 'DCA']
                },
                'yearly_vol': {
                    'Market (SPY)': spy_results.stats.loc['yearly_vol', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_vol', 'DCA']
                }
            }
            
            return jsonify({
                'plot_url': f"/static/plots/{image_filename}",
                'comparison_data': comparison_data
            }), 200
            
        except Exception as e:
            logger.error(f"DCA 백테스팅 오류: {e}")
            return jsonify({'error': f'백테스팅 수행 중 오류가 발생했습니다: {str(e)}'}), 500

    # (9) MA Cross 전략 백테스팅 API 수정
    @app.route('/api/backtest_macross', methods=['POST'])
    def api_backtest_macross():
        data = request.get_json()
        
        # 입력값 검증
        required_fields = ['tickers', 'short_ma', 'long_ma', 'start_date', 'end_date']
        if not all(field in data for field in required_fields):
            return jsonify({'error': '모든 입력값을 제공해야 합니다.'}), 400
        
        tickers = data['tickers']
        short_ma = int(data['short_ma'])
        long_ma = int(data['long_ma'])
        start_date = data['start_date']
        end_date = data['end_date']
        
        if not tickers or short_ma >= long_ma:
            return jsonify({'error': '입력값이 올바르지 않습니다.'}), 400
        
        try:
            # 백테스터 인스턴스 생성
            backtester = MACrossBacktester()
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"macross_{timestamp}.png"
            image_path = os.path.join(PLOT_DIR, image_filename)
            
            # 전략 백테스트 실행
            results, price_data = backtester.run_backtest(
                tickers, short_ma, long_ma, start_date, end_date
            )
            
            # SPY 백테스트 실행
            spy_results = run_buyandhold_backtest(['SPY'], {'SPY': 1.0}, start_date, end_date)
            
            # 결과 플롯 생성
            backtester.plot_results(
                results, price_data, start_date, end_date,
                'Moving Average Crossover Strategy with Forecast and Signals',
                image_path
            )
            
            # 비교 데이터 생성
            comparison_data = {
                'total_return': {
                    'Market (SPY)': spy_results.stats.loc['total_return', 'BuyAndHold'],
                    'Strategy': results.stats.loc['total_return', 'MA_Crossover']  # 여기를 수정
                },
                'yearly_mean': {
                    'Market (SPY)': spy_results.stats.loc['yearly_mean', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_mean', 'MA_Crossover']  # 여기를 수정
                },
                'yearly_vol': {
                    'Market (SPY)': spy_results.stats.loc['yearly_vol', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_vol', 'MA_Crossover']  # 여기를 수정
                }
            }
            
            return jsonify({
                'plot_url': f"/static/plots/{image_filename}",
                'comparison_data': comparison_data
            }), 200
            
        except Exception as e:
            logger.error(f"MA Cross 백테스팅 오류: {str(e)}", exc_info=True)
            return jsonify({'error': f'백테스팅 수행 중 오류가 발생했습니다: {str(e)}'}), 500

    # (10) 모멘텀 전략 백테스팅 API 수정
    @app.route('/api/backtest_momentum', methods=['POST'])
    def api_backtest_momentum():
        try:
            data = request.get_json()
            tickers = data.get('tickers', [])
            lookback = data.get('lookback')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            # 입력 검증
            if not tickers or not lookback or not start_date or not end_date:
                return jsonify({'error': '모든 입력값을 제공해야 합니다.'}), 400
            
            if lookback < 20:
                return jsonify({'error': 'lookback 기간은 최소 20이어야 합니다.'}), 400
            
            # 백테스터 인스턴스 생성
            backtester = MomentumBacktester()
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"momentum_{timestamp}.png"
            image_path = os.path.join(PLOT_DIR, image_filename)

            # 전략 백테스트 실행
            results = backtester.run_backtest(tickers, lookback, start_date, end_date)
            
            # SPY 백테스트 실행
            spy_results = run_buyandhold_backtest(['SPY'], {'SPY': 1.0}, start_date, end_date)
            
            # 데이터 가져오기 및 플롯 생성
            market_data = backtester.fetch_data(tickers, start_date, end_date, lookback)
            backtester.plot_results(
                results=results,
                data=market_data,
                start_date=start_date,
                end_date=end_date,
                title='Momentum Strategy with Forecast and Buy Signals',
                tickers=tickers,
                image_path=image_path
            )
            
            # 비교 데이터 생성
            comparison_data = {
                'total_return': {
                    'Market (SPY)': spy_results.stats.loc['total_return', 'BuyAndHold'],
                    'Strategy': results.stats.loc['total_return', 'Momentum']
                },
                'yearly_mean': {
                    'Market (SPY)': spy_results.stats.loc['yearly_mean', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_mean', 'Momentum']
                },
                'yearly_vol': {
                    'Market (SPY)': spy_results.stats.loc['yearly_vol', 'BuyAndHold'],
                    'Strategy': results.stats.loc['yearly_vol', 'Momentum']
                }
            }
            
            return jsonify({
                'plot_url': f"/static/plots/{image_filename}",
                'comparison_data': comparison_data
            }), 200
            
        except Exception as e:
            logger.error(f"Momentum 백테스팅 오류: {str(e)}", exc_info=True)
            return jsonify({'error': f'백테스팅 수행 중 오류가 발생했습니다: {str(e)}'}), 500

    # Helper 함수: 비중의 합이 가까운지 확인 (JavaScript의 isClose와 유사)
    def is_close(a, b, tol):
        return abs(a - b) < tol

    return app
