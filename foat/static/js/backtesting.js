// static/js/backtesting.js

document.addEventListener('DOMContentLoaded', function() {
  // 백테스팅 폼 요소들
  const addAssetBtn = document.getElementById('add-asset-btn');
  const assetModal = document.getElementById('asset-modal');
  const closeModalBtn = document.getElementById('close-modal-btn');
  const assetSearchInput = document.getElementById('asset-search-input');
  const searchResultsDiv = document.getElementById('search-results');
  const assetsListDiv = document.getElementById('assets-list');
  const backtestForm = document.getElementById('backtest-form');
  const backtestRunBtn = document.getElementById('backtest-run-btn');
  const strategySelect = document.getElementById('strategy');
  const strategySpecificInputs = document.getElementById('strategy-specific-inputs');
  const backtestResultDiv = document.getElementById('backtest-result');
  const resultPlot = document.getElementById('result-plot');
  const resultMu = document.getElementById('result-mu');
  const resultSe = document.getElementById('result-se');
  const resultExpected = document.getElementById('result-expected');
  
  // 자산 목록 (Python의 tuple을 흉내 내기 위한 배열)
  let assets = []; // ['AAPL', 'MSFT', 'GOOGL']
  let searchTimeout = null; // 검색 딜레이를 위한 타이머
  
  // 전략별 입력 필드
  function renderStrategyInputs(strategy) {
      strategySpecificInputs.innerHTML = ''; // 초기화
      
      if (strategy === 'buyandhold' || strategy === 'dca') {
          // 자산별 비중 입력 섹션
          const weightsDiv = document.createElement('div');
          weightsDiv.classList.add('mb-4');
          weightsDiv.innerHTML = `
              <label class="block text-gray-700">각 자산의 비중 (0 ~ 1):</label>
              <div id="weights-inputs" class="mt-2">
                  <!-- 자산별 비중 입력 필드가 여기에 추가됩니다 -->
              </div>
          `;
          strategySpecificInputs.appendChild(weightsDiv);
      }
      
      if (strategy === 'dca') {
          // 투자 주기 선택 섹션
          const periodDiv = document.createElement('div');
          periodDiv.classList.add('mb-4');
          periodDiv.innerHTML = `
              <label class="block text-gray-700">투자 주기:</label>
              <select id="investment-period" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm">
                  <option value="M">매달</option>
                  <option value="W">매주</option>
                  <option value="D">매 영업일</option>
              </select>
          `;
          strategySpecificInputs.appendChild(periodDiv);
      }
      
      if (strategy === 'macross') {
          // 장단기 MA 교차 전략: 단기 MA, 장기 MA 입력
          const shortMaDiv = document.createElement('div');
          shortMaDiv.classList.add('mb-4');
          shortMaDiv.innerHTML = `
              <label class="block text-gray-700">단기 MA 기간:</label>
              <input type="number" id="short-ma" min="1" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required>
          `;
          
          const longMaDiv = document.createElement('div');
          longMaDiv.classList.add('mb-4');
          longMaDiv.innerHTML = `
              <label class="block text-gray-700">장기 MA 기간:</label>
              <input type="number" id="long-ma" min="1" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required>
          `;
          
          strategySpecificInputs.appendChild(shortMaDiv);
          strategySpecificInputs.appendChild(longMaDiv);
      } else if (strategy === 'momentum') {
          // 모멘텀 전략: lookback 기간 입력
          const lookbackDiv = document.createElement('div');
          lookbackDiv.classList.add('mb-4');
          lookbackDiv.innerHTML = `
              <label class="block text-gray-700">Lookback 기간:</label>
              <input type="number" id="lookback" min="20" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required>
          `;
          
          strategySpecificInputs.appendChild(lookbackDiv);
      }
      
      // 날짜 입력 필드 (모든 전략에 공통)
      const dateDiv = document.createElement('div');
      dateDiv.classList.add('mb-4');
      dateDiv.innerHTML = `
          <label class="block text-gray-700">시작일:</label>
          <input type="date" id="start-date" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required>
      `;
      strategySpecificInputs.appendChild(dateDiv);
      
      const endDateDiv = document.createElement('div');
      endDateDiv.classList.add('mb-4');
      endDateDiv.innerHTML = `
          <label class="block text-gray-700">종료일:</label>
          <input type="date" id="end-date" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" required>
      `;
      strategySpecificInputs.appendChild(endDateDiv);
  }
  
  // 초기 전략 입력 렌더링
  renderStrategyInputs(strategySelect.value);
  
  // 전략 선택 시 입력 필드 변경
  strategySelect.addEventListener('change', function() {
      renderStrategyInputs(this.value);
      validateForm();
  });
  
  // 자산 추가 버튼 클릭 시 모달 열기
  addAssetBtn.addEventListener('click', function() {
      assetModal.classList.remove('hidden');
      assetSearchInput.focus();
  });
  
  // 모달 닫기 버튼 클릭 시 모달 닫기
  closeModalBtn.addEventListener('click', function() {
      assetModal.classList.add('hidden');
      assetSearchInput.value = '';
      searchResultsDiv.innerHTML = '';
      searchResultsDiv.classList.add('hidden');
      clearTimeout(searchTimeout);
  });
  
  // 자산 검색 입력 시 실시간 검색
  assetSearchInput.addEventListener('input', function() {
      const query = this.value.trim();
      if (query.length === 0) {
          searchResultsDiv.innerHTML = '';
          searchResultsDiv.classList.add('hidden');
          clearTimeout(searchTimeout);
          return;
      }
      
      // 딜레이 후 검색 (사용자 입력이 멈춘 후 300ms)
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
          performSearch(query);
      }, 300);
  });
  
  // 검색 수행 함수
  function performSearch(query) {
      fetch(`/api/search_ticker?keyword=${encodeURIComponent(query)}`)
          .then(response => response.json())
          .then(data => {
              if (data.error) {
                  displaySearchResults([]);
                  return;
              }
              displaySearchResults(data.results);
          })
          .catch(error => {
              console.error('Error:', error);
              displaySearchResults([]);
          });
  }
  
  // 검색 결과 표시
  function displaySearchResults(results) {
      searchResultsDiv.innerHTML = '';
      if (results.length === 0) {
          searchResultsDiv.innerHTML = '<li class="px-4 py-2">검색 결과가 없습니다.</li>';
          searchResultsDiv.classList.remove('hidden');
          return;
      }
      
      results.forEach(item => {
          const resultItem = document.createElement('li');
          resultItem.className = 'px-4 py-2 hover:bg-gray-200 cursor-pointer';
          resultItem.innerHTML = `
              <span>${item.Name} (${item.Symbol})</span>
          `;
          resultItem.addEventListener('click', function() {
              const symbol = item.Symbol;
              const name = item.Name;
              addAsset(symbol, name);
              assetModal.classList.add('hidden');
              assetSearchInput.value = '';
              searchResultsDiv.innerHTML = '';
              searchResultsDiv.classList.add('hidden');
          });
          searchResultsDiv.appendChild(resultItem);
      });
      searchResultsDiv.classList.remove('hidden');
  }
  
  // 자산 목록에 추가
  function addAsset(symbol, name) {
      // 이미 추가된 자산인지 확인
      if (assets.includes(symbol)) {
          alert('이미 추가된 자산입니다.');
          return;
      }
      
      assets.push(symbol);
      renderAssets();
      renderWeightsInputs();
      validateForm();
  }
  
  // 자산 목록 렌더링 함수
  function renderAssets() {
      // 자산 리스트를 수평으로 나열하도록 스타일 적용
      assetsListDiv.innerHTML = '';
      
      assets.forEach((ticker, index) => {
          const assetDiv = document.createElement('div');
          assetDiv.classList.add('asset-item');
          assetDiv.innerHTML = `
              <span>'${ticker}'</span>
              <button type="button" class="remove-asset-btn px-2 py-1 bg-red-500 text-white rounded-md">삭제</button>
          `;
          assetsListDiv.appendChild(assetDiv);
      });
      
      // 삭제 버튼 이벤트 추가
      const removeButtons = document.querySelectorAll('.remove-asset-btn');
      removeButtons.forEach(button => {
          button.addEventListener('click', function() {
              const ticker = this.parentElement.querySelector('span').textContent.slice(1, -1); // 'AAPL' -> AAPL
              if (confirm('삭제하시겠습니까?')) {
                  removeAsset(ticker);
              }
          });
      });
  }
  
  // 자산 삭제 함수
  function removeAsset(ticker) {
      const index = assets.indexOf(ticker);
      if (index > -1) {
          assets.splice(index, 1);
          renderAssets();
          renderWeightsInputs();
          validateForm();
      }
  }
  
  // 비중 입력 필드 렌더링 함수
  function renderWeightsInputs() {
      const strategy = strategySelect.value;
      if (strategy !== 'buyandhold' && strategy !== 'dca') {
          return;
      }
      const weightsInputsDiv = document.getElementById('weights-inputs');
      weightsInputsDiv.innerHTML = '';
      
      assets.forEach(ticker => {
          const weightDiv = document.createElement('div');
          weightDiv.classList.add('mb-2', 'flex', 'items-center');
          weightDiv.innerHTML = `
              <label class="w-24 text-gray-700">${ticker}:</label>
              <input type="number" step="0.01" min="0" max="1" class="weight-input border border-gray-300 rounded-md p-1" data-symbol="${ticker}" required>
          `;
          weightsInputsDiv.appendChild(weightDiv);
      });
  }
  
  // 비중 합계 검증 함수
  function validateWeights() {
      const strategy = strategySelect.value;
      if (strategy !== 'buyandhold' && strategy !== 'dca') {
          return true;
      }
      const weightInputs = document.querySelectorAll('.weight-input');
      let total = 0;
      weightInputs.forEach(input => {
          const val = parseFloat(input.value);
          if (isNaN(val) || val < 0 || val > 1) {
              total = -1; // Invalid input
          } else {
              total += val;
          }
      });
      return isClose(total, 1.0, 0.01);
  }
  
  // 폼 검증 함수
  function validateForm() {
      // 전략별 추가 입력 사항 확인
      const strategy = strategySelect.value;
      let valid = true;
      
      if (strategy === 'buyandhold' || strategy === 'dca') {
          const weightsValid = validateWeights();
          if (!weightsValid) {
              valid = false;
          }
      }
      
      if (strategy === 'macross') {
          const shortMa = document.getElementById('short-ma').value;
          const longMa = document.getElementById('long-ma').value;
          if (!shortMa || !longMa || parseInt(shortMa) <= 0 || parseInt(longMa) <= 0) {
              valid = false;
          }
      } else if (strategy === 'momentum') {
          const lookback = document.getElementById('lookback').value;
          if (!lookback || parseInt(lookback) < 20) {
              valid = false;
          }
      }
      
      // 날짜 입력 확인
      const startDate = document.getElementById('start-date').value;
      const endDate = document.getElementById('end-date').value;
      if (!startDate || !endDate) {
          valid = false;
      }
      
      // 자산 목록이 비어있는지 확인
      if (assets.length === 0) {
          valid = false;
      }
      
      // 비중 합계가 1인지 확인
      if ((strategy === 'buyandhold' || strategy === 'dca') && !validateWeights()) {
          valid = false;
      }
      
      backtestRunBtn.disabled = !valid;
  }
  
  // Helper 함수: isClose 구현 (0.01 허용 오차)
  function isClose(a, b, tol) {
      return Math.abs(a - b) < tol;
  }
  
  // 폼 입력 이벤트
  backtestForm.addEventListener('input', validateForm);
  
  // 백테스팅 실행
backtestForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    if (assets.length === 0) {
        alert('적어도 하나 이상의 자산을 추가해야 합니다.');
        return;
    }
    
    const strategy = strategySelect.value;
    let payload = {
        tickers: assets,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value
    };
    
    if (strategy === 'buyandhold' || strategy === 'dca') {
        const weightInputs = document.querySelectorAll('.weight-input');
        let weights = {};
        weightInputs.forEach(input => {
            const symbol = input.getAttribute('data-symbol');
            const weight = parseFloat(input.value);
            weights[symbol] = weight;
        });
        payload.weights = weights;
    }
    
    let apiEndpoint;
    if (strategy === 'buyandhold') {
        // 매수&보유 전략
        apiEndpoint = '/api/backtest_buyandhold';
    } else if (strategy === 'dca') {
        // 분할매수 전략
        const period = document.getElementById('investment-period').value;
        payload.period = period;
        apiEndpoint = '/api/backtest_dca';
    } else if (strategy === 'macross') {
        // 장단기 MA 교차 전략
        const short_ma = parseInt(document.getElementById('short-ma').value);
        const long_ma = parseInt(document.getElementById('long-ma').value);
        payload.short_ma = short_ma;
        payload.long_ma = long_ma;
        apiEndpoint = '/api/backtest_macross';
    } else if (strategy === 'momentum') {
        // 모멘텀 전략
        const lookback = parseInt(document.getElementById('lookback').value);
        payload.lookback = lookback;
        apiEndpoint = '/api/backtest_momentum';
    }
    
    // 백테스팅 API 호출
    fetch(apiEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            // 결과 표시
            document.getElementById('result-plot').src = data.plot_url;
            
            // 비교 테이블 데이터 업데이트
            const formatNumber = (num) => (num * 100).toFixed(2) + '%';
            
            // 총 수익률 업데이트
            document.getElementById('spy-total-return').textContent = 
                formatNumber(data.comparison_data.total_return['Market (SPY)']);
            document.getElementById('strategy-total-return').textContent = 
                formatNumber(data.comparison_data.total_return.Strategy);
            
            // 연간 수익률 업데이트
            document.getElementById('spy-yearly-return').textContent = 
                formatNumber(data.comparison_data.yearly_mean['Market (SPY)']);
            document.getElementById('strategy-yearly-return').textContent = 
                formatNumber(data.comparison_data.yearly_mean.Strategy);
            
            // 연간 변동성 업데이트
            document.getElementById('spy-yearly-vol').textContent = 
                formatNumber(data.comparison_data.yearly_vol['Market (SPY)']);
            document.getElementById('strategy-yearly-vol').textContent = 
                formatNumber(data.comparison_data.yearly_vol.Strategy);
            
            // 결과 영역 표시
            document.getElementById('backtest-result').classList.remove('hidden');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('백테스팅 수행 중 오류가 발생했습니다.');
    });
});
});