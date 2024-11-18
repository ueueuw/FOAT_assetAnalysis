# app.py

from flask import Flask
from flask_cors import CORS
import os, logging
import matplotlib

from controller import register_routes

# GUI 백엔드 비활성화
matplotlib.use('Agg')

def create_app():
    app = Flask(__name__)
    CORS(app)  # 모든 도메인에서의 요청을 허용

    # 서버 시작 시 플롯 저장 디렉토리 존재 확인 및 생성
    PLOT_DIR = os.path.join('static', 'plots')
    if not os.path.exists(PLOT_DIR):
        os.makedirs(PLOT_DIR)
        
    # 로깅 설정
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

    
    # 라우트 등록
    register_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=False)  # 디버깅 모드 비활성화
    