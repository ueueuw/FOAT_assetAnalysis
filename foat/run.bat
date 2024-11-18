@echo off
:: 가상 환경 활성화 (가상 환경이 있는 경우)
if exist ".\Scripts\activate.bat" (
    call .\Scripts\activate
)

:: Flask 서버 실행
echo Starting Flask server...
start http://127.0.0.1:5000
python app.py
