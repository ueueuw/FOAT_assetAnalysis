// static/js/lab.js

document.addEventListener('DOMContentLoaded', function () {
  const labForm = document.getElementById('labForm');
  const buyThresholdInput = document.getElementById('buyThreshold');
  const sellThresholdInput = document.getElementById('sellThreshold');
  const startDateInput = document.getElementById('startDate');
  const endDateInput = document.getElementById('endDate');
  const backtestBtn = document.getElementById('backtestBtn');
  const backtestResultDiv = document.getElementById('backtestResult');
  const backtestPlotImg = document.getElementById('backtestPlot');
  const backtestMetricsDiv = document.getElementById('backtestMetrics');
  
  // 백테스팅 메트릭스 테이블의 셀 요소
  const marketTotalReturn = document.getElementById('marketTotalReturn');
  const strategyTotalReturn = document.getElementById('strategyTotalReturn');
  const marketAnnualReturn = document.getElementById('marketAnnualReturn');
  const strategyAnnualReturn = document.getElementById('strategyAnnualReturn');
  const marketVolatility = document.getElementById('marketVolatility');
  const strategyVolatility = document.getElementById('strategyVolatility');
  
  // 입력값 유효성 검사 함수
  function validateInputs() {
    const buyThreshold = parseFloat(buyThresholdInput.value);
    const sellThreshold = parseFloat(sellThresholdInput.value);
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;
    
    const isBuyValid = !isNaN(buyThreshold) && buyThreshold >= 0 && buyThreshold <= 100;
    const isSellValid = !isNaN(sellThreshold) && sellThreshold >= 0 && sellThreshold <= 100;
    const isStartDateValid = startDate >= '2011-01-03' && startDate <= '2022-12-30';
    const isEndDateValid = endDate >= '2011-01-03' && endDate <= '2022-12-30';
    const isDateRangeValid = startDate <= endDate;
    
    if (isBuyValid && isSellValid && isStartDateValid && isEndDateValid && isDateRangeValid) {
      backtestBtn.disabled = false;
    } else {
      backtestBtn.disabled = true;
    }
  }
  
  // 입력 이벤트 리스너 추가
  buyThresholdInput.addEventListener('input', validateInputs);
  sellThresholdInput.addEventListener('input', validateInputs);
  startDateInput.addEventListener('input', validateInputs);
  endDateInput.addEventListener('input', validateInputs);
  
  // 전략 백테스트 폼 제출 이벤트
  labForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const buyThreshold = parseFloat(buyThresholdInput.value);
    const sellThreshold = parseFloat(sellThresholdInput.value);
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;
    
    // 추가적인 유효성 검사
    if (
      isNaN(buyThreshold) || buyThreshold < 0 || buyThreshold > 100 ||
      isNaN(sellThreshold) || sellThreshold < 0 || sellThreshold > 100 ||
      startDate < '2011-01-03' || startDate > '2022-12-30' ||
      endDate < '2011-01-03' || endDate > '2022-12-30' ||
      startDate > endDate
    ) {
      alert('입력값을 올바르게 입력해주세요.');
      return;
    }
    
    // 백엔드로 데이터 전송 및 결과 받기
    fetch('/api/backtest_fgi', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        buy_threshold: buyThreshold, 
        sell_threshold: sellThreshold, 
        start_date: startDate,
        end_date: endDate
      }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        alert(`오류: ${data.error}`);
      } else {
        // 백테스팅 결과 이미지 표시
        backtestPlotImg.src = data.plot_url;
        
        // 백테스팅 메트릭스 테이블 업데이트
        marketTotalReturn.textContent = `${data.metrics['Total Return (Market)'].toFixed(2)}%`;
        strategyTotalReturn.textContent = `${data.metrics['Total Return (Strategy)'].toFixed(2)}%`;
        marketAnnualReturn.textContent = `${data.metrics['Annual Return (Market)'].toFixed(2)}%`;
        strategyAnnualReturn.textContent = `${data.metrics['Annual Return (Strategy)'].toFixed(2)}%`;
        marketVolatility.textContent = `${data.metrics['Volatility (Market)'].toFixed(2)}%`;
        strategyVolatility.textContent = `${data.metrics['Volatility (Strategy)'].toFixed(2)}%`;
        
        // 결과 표시 영역 보이기
        backtestResultDiv.classList.remove('hidden');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('백테스팅 실행 중 오류가 발생했습니다.');
    });
  });
});