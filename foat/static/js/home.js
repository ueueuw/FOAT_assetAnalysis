// static/js/home.js

document.addEventListener('DOMContentLoaded', function () {
  // Chart.js 원형 그래프 초기화
  const ctx = document.getElementById('assetChart').getContext('2d');
  const assetChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: [],
      datasets: [{
        data: [],
        backgroundColor: ['#4F46E5', '#10B981', '#EF4444', '#F59E0B', '#84CC16', '#3B82F6', '#DB2777', '#9333EA', '#14B8A6', '#F97316'],
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
        },
      }
    },
  });

  // 자산 및 종목 데이터 관리
  let currentCash = 0;
  let stockHoldings = {};

  // 모달 제어
  const setAssetBtn = document.getElementById('setAssetBtn');
  const setAssetModal = document.getElementById('setAssetModal');
  const closeSetAssetModal = document.getElementById('closeSetAssetModal');
  const setAssetForm = document.getElementById('setAssetForm');
  const addStockBtn = document.getElementById('addStockBtn');
  const addStockModal = document.getElementById('addStockModal');
  const closeAddStockModal = document.getElementById('closeAddStockModal');
  const addStockForm = document.getElementById('addStockForm');
  const stockSearchInput = document.getElementById('stockSearch');
  const stockSearchResults = document.getElementById('stockSearchResults');
  
  const setTargetBtn = document.getElementById('setTargetBtn');
  const setTargetModal = document.getElementById('setTargetModal');
  const closeSetTargetModal = document.getElementById('closeSetTargetModal');
  const setTargetForm = document.getElementById('setTargetForm');
  const requiredReturnDiv = document.getElementById('requiredReturn');
  
  const assetList = document.getElementById('assetList'); // 자산 목록 UL 요소
  const totalAssetSpan = document.getElementById('totalAsset'); // 총 자산액 표시 요소

  // 보유 종목 수량 조정 모달 제어
  const adjustShareModal = document.getElementById('adjustShareModal');
  const closeAdjustShareModal = document.getElementById('closeAdjustShareModal');
  const adjustShareForm = document.getElementById('adjustShareForm');
  const adjustSymbolInput = document.getElementById('adjustSymbol');
  const adjustShareInput = document.getElementById('adjustShare');

  // 로컬 스토리지 키
  const STORAGE_KEY = 'user_assets';

  // 자산 설정 모달 열기
  setAssetBtn.addEventListener('click', function () {
    setAssetModal.classList.remove('hidden');
    populateAssetForm();
  });
  
  // 자산 설정 모달 닫기
  closeSetAssetModal.addEventListener('click', function () {
    setAssetModal.classList.add('hidden');
    setAssetForm.reset();
  });
  
  // 종목 추가 모달 열기
  addStockBtn.addEventListener('click', function () {
    addStockModal.classList.remove('hidden');
  });
  
  // 종목 추가 모달 닫기
  closeAddStockModal.addEventListener('click', function () {
    addStockModal.classList.add('hidden');
    addStockForm.reset();
    stockSearchResults.classList.add('hidden');
  });
  
  // 종목 검색
  stockSearchInput.addEventListener('input', function () {
    const keyword = this.value.trim();
    if (keyword.length === 0) {
      stockSearchResults.innerHTML = '';
      stockSearchResults.classList.add('hidden');
      return;
    }
    
    fetch(`/api/search_ticker?keyword=${encodeURIComponent(keyword)}`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          stockSearchResults.innerHTML = `<li class="px-4 py-2">${data.error}</li>`;
          stockSearchResults.classList.remove('hidden');
          return;
        }
        
        if (data.results.length === 0) {
          stockSearchResults.innerHTML = '<li class="px-4 py-2">검색 결과가 없습니다.</li>';
          stockSearchResults.classList.remove('hidden');
          return;
        }
        
        stockSearchResults.innerHTML = '';
        data.results.forEach(item => {
          const li = document.createElement('li');
          li.className = 'px-4 py-2 hover:bg-gray-200 cursor-pointer';
          li.textContent = `${item.Symbol} - ${item.Name}`;
          li.addEventListener('click', function () {
            document.getElementById('stockSymbol').value = item.Symbol;
            stockSearchResults.innerHTML = '';
            stockSearchResults.classList.add('hidden');
          });
          stockSearchResults.appendChild(li);
        });
        stockSearchResults.classList.remove('hidden');
      })
      .catch(error => {
        console.error('Error:', error);
        stockSearchResults.innerHTML = '<li class="px-4 py-2">검색 중 오류가 발생했습니다.</li>';
        stockSearchResults.classList.remove('hidden');
      });
  });
  
  // 종목 추가 폼 제출
  addStockForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const symbol = document.getElementById('stockSymbol').value.trim();
    const share = parseFloat(document.getElementById('stockShare').value);
    
    if (!symbol || isNaN(share) || share < 0) {
      alert('종목과 수량을 올바르게 입력해주세요.');
      return;
    }
    
    // 이미 보유 중인 종목인지 확인
    if (stockHoldings[symbol]) {
      stockHoldings[symbol] += share;
    } else {
      stockHoldings[symbol] = share;
    }
    
    addStockModal.classList.add('hidden');
    addStockForm.reset();
    stockSearchResults.classList.add('hidden');
    populateStockHoldings();
  });
  
  // 자산 설정 폼 제출
  setAssetForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const cashInput = document.getElementById('currentCash').value;
    const currentCashValue = parseFloat(cashInput);
    
    if (isNaN(currentCashValue) || currentCashValue < 0) {
      alert('현금 자산을 올바르게 입력해주세요.');
      return;
    }
    
    // 자산 데이터 수집
    const assetData = {
      current_cash: currentCashValue,
      stock_holdings: stockHoldings
    };
    
    fetch('/api/set_asset', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(assetData),
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
      } else {
        alert('자산이 설정되었습니다.');
        setAssetModal.classList.add('hidden');
        setAssetForm.reset();
        // 현금 자산 업데이트
        currentCash = data.current_cash;
        // 종목 보유 정보 업데이트
        stockHoldings = data.stock_holdings;
        populateStockHoldings();
        // 자산 그래프 업데이트
        assetChart.data.labels = data.labels;
        assetChart.data.datasets[0].data = data.sizes;
        assetChart.update();
        // 자산 목록 업데이트
        populateAssetList();
        // 총 자산액 업데이트
        updateTotalAsset();
        // 로컬 스토리지에 저장
        saveAssetsToLocalStorage();
        // '목표 금액 설정' 버튼 표시
        setTargetBtn.classList.remove('hidden');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('자산 설정 중 오류가 발생했습니다.');
    });
  });
  
  // 목표 금액 설정 모달 열기
  setTargetBtn.addEventListener('click', function () {
    setTargetModal.classList.remove('hidden');
  });
  
  // 목표 금액 설정 모달 닫기
  closeSetTargetModal.addEventListener('click', function () {
    setTargetModal.classList.add('hidden');
    setTargetForm.reset();
  });
  
  // 목표 금액 설정 폼 제출
  setTargetForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const targetAsset = parseFloat(document.getElementById('targetAsset').value);
    const years = parseInt(document.getElementById('years').value);
    
    if (isNaN(targetAsset) || targetAsset <= 0 || isNaN(years) || years <= 0) {
      alert('목표 자산과 기간을 올바르게 입력해주세요.');
      return;
    }
    
    // 현재 자산을 계산 (현금 + 종목 보유액)
    calculateCurrentAsset().then(currentAsset => {
      fetch('/api/calculate_required_return', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ current_asset: currentAsset, target_asset: targetAsset, years: years }),
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          alert(data.error);
        } else {
          alert('목표 자산이 설정되었습니다.');
          setTargetModal.classList.add('hidden');
          setTargetForm.reset();
          // 수익률 결과 표시
          requiredReturnDiv.innerHTML = `
            <p class="text-lg">목표 자산을 달성하기 위해서는 연간 <span class="font-bold text-green-600">${data.required_return_per_year.toFixed(2)}%</span>의 수익률이 필요합니다.</p>
          `;
        }
      })
      .catch(error => {
        console.error('Error:', error);
        alert('목표 설정 중 오류가 발생했습니다.');
      });
    });
  });
  
  // 종목 보유 목록 표시 및 클릭 시 보유 수량 조정 모달 열기
  function populateStockHoldings() {
    const holdingsDiv = document.getElementById('stockHoldings');
    holdingsDiv.innerHTML = '';
    
    for (const [symbol, share] of Object.entries(stockHoldings)) {
      const div = document.createElement('div');
      div.className = 'flex items-center justify-between p-2 border rounded cursor-pointer';
      div.title = '보유 수량 조정';
      
      const info = document.createElement('span');
      info.textContent = `${symbol}: ${share}`;
      
      // 클릭 시 보유 수량 조정 모달 열기
      div.addEventListener('click', function () {
        openAdjustShareModal(symbol, share);
      });
      
      div.appendChild(info);
      holdingsDiv.appendChild(div);
    }
  }
  
  // 보유 수량 조정 모달 열기 함수
  function openAdjustShareModal(symbol, currentShare) {
    adjustSymbolInput.value = symbol;
    adjustShareInput.value = currentShare;
    adjustShareModal.classList.remove('hidden');
  }
  
  // 보유 수량 조정 모달 닫기
  closeAdjustShareModal.addEventListener('click', function () {
    adjustShareModal.classList.add('hidden');
    adjustShareForm.reset();
  });
  
  // 보유 수량 조정 폼 제출
  adjustShareForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const symbol = adjustSymbolInput.value.trim();
    const newShare = parseFloat(adjustShareInput.value);
    
    // 수정된 검증 로직: 0 이상 실수인지 확인
    if (!symbol || isNaN(newShare) || newShare < 0) {
      alert('보유수량을 올바르게 입력해주세요.');
      return;
    }
    
    if (newShare === 0) {
      // 보유 수량이 0인 경우 해당 종목 삭제
      delete stockHoldings[symbol];
    } else {
      // 보유 수량 업데이트
      stockHoldings[symbol] = newShare;
    }
    
    adjustShareModal.classList.add('hidden');
    adjustShareForm.reset();
    populateStockHoldings();
    populateAssetList(); // 자산 목록 업데이트
    updateChart(); // 그래프 업데이트
    updateTotalAsset(); // 총 자산액 업데이트
    saveAssetsToLocalStorage(); // 로컬 스토리지 업데이트
  });

  // 자산 목록 표시 함수
  async function populateAssetList() {
    assetList.innerHTML = '';
    const assetDetails = [];

    // 현금 자산 추가 (항상 최상단에 위치)
    assetDetails.push({
      name: '현금',
      amount: currentCash
    });

    // 종목 자산 추가
    for (const [symbol, share] of Object.entries(stockHoldings)) {
      const price = await fetchStockPrice(symbol); // 주식 가격을 가져오는 함수
      const amount = share * price;
      assetDetails.push({
        name: symbol,
        amount: amount
      });
    }

    // '현금'을 제외한 종목들을 보유액 내림차순으로 정렬
    const sortedStocks = assetDetails.slice(1).sort((a, b) => b.amount - a.amount);

    // 정렬된 종목들을 다시 배열에 추가 ('현금'을 항상 첫 번째에 유지)
    const finalAssetDetails = [assetDetails[0], ...sortedStocks];

    // 목록에 추가
    finalAssetDetails.forEach(asset => {
      const li = document.createElement('li');
      li.className = 'flex justify-between p-2 bg-white rounded shadow mb-2';
      li.innerHTML = `<span>${asset.name}</span><span>$${asset.amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>`; // 원화에서 달러화로 변경
      assetList.appendChild(li);
    });

    // 총 자산액 업데이트
    updateTotalAsset();
  }

  // 총 자산액 업데이트 함수
  function updateTotalAsset() {
    calculateCurrentAsset().then(totalAsset => {
      totalAssetSpan.textContent = `$${totalAsset.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    });
  }

  // 현재 자산 계산 함수 (현금 + 종목 보유액)
  async function calculateCurrentAsset() {
    let total = currentCash;
    for (const [symbol, share] of Object.entries(stockHoldings)) {
      const price = await fetchStockPrice(symbol);
      total += share * price;
    }
    return total;
  }

  // 주식 가격을 가져오는 함수 (비동기)
  async function fetchStockPrice(symbol) {
    try {
      const response = await fetch(`/api/get_stock_price?symbol=${encodeURIComponent(symbol)}`);
      const data = await response.json();
      if (data.error) {
        console.error(`Error fetching price for ${symbol}:`, data.error);
        return 0;
      }
      return data.price;
    } catch (error) {
      console.error(`Error fetching price for ${symbol}:`, error);
      return 0;
    }
  }

  // 자산 그래프 업데이트 함수
  async function updateChart() {
    // 자산 데이터 수집
    const assetData = {
      current_cash: currentCash,
      stock_holdings: stockHoldings
    };
    
    try {
      const response = await fetch('/api/set_asset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(assetData),
      });
      const data = await response.json();
      if (!data.error) {
        assetChart.data.labels = data.labels;
        assetChart.data.datasets[0].data = data.sizes;
        assetChart.update();
        populateAssetList(); // 자산 목록 업데이트
        saveAssetsToLocalStorage(); // 로컬 스토리지 업데이트
      }
    } catch (error) {
      console.error('Error updating chart:', error);
    }
  }
  
  // 자산 설정 폼에 이전 자산 정보 표시
  function populateAssetForm() {
    // 로컬 스토리지에서 자산 데이터 로드
    loadAssetsFromLocalStorage();

    document.getElementById('currentCash').value = currentCash;
    populateStockHoldings();
    // 자산 데이터가 있을 경우 차트 업데이트
    if (currentCash > 0 || Object.keys(stockHoldings).length > 0) {
      updateChart(); // 페이지 로드 시 차트 업데이트
    }
  }

  // 로컬 스토리지에 자산 데이터 저장
  function saveAssetsToLocalStorage() {
    const assetData = {
      current_cash: currentCash,
      stock_holdings: stockHoldings
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(assetData));
  }

  // 로컬 스토리지에서 자산 데이터 로드
  function loadAssetsFromLocalStorage() {
    const storedData = localStorage.getItem(STORAGE_KEY);
    if (storedData) {
      try {
        const assetData = JSON.parse(storedData);
        currentCash = assetData.current_cash || 0;
        stockHoldings = assetData.stock_holdings || {};
        // assetChart.data.labels = assetData.labels || [];
        // assetChart.data.datasets[0].data = assetData.sizes || [];
        // assetChart.update(); // Update will be handled in updateChart()
        // populateAssetList(); // Asset list will be handled in updateChart()
      } catch (e) {
        console.error('로컬 스토리지 데이터 파싱 오류:', e);
      }
    }
  }

  // 초기 페이지 로드 시 자산 데이터 로드 및 차트 업데이트
  loadAssetsFromLocalStorage();
  if (currentCash > 0 || Object.keys(stockHoldings).length > 0) {
    updateChart(); // 자산 데이터가 있을 경우 차트 업데이트
  }
  // populateAssetList(); // 이 라인은 중복 호출을 방지하기 위해 제거했습니다.
});