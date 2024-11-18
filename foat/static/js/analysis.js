// static/js/analysis.js

document.addEventListener('DOMContentLoaded', function () {
  // 탭 전환 로직
  const tabCorr = document.getElementById('tabCorr');
  const tabRanking = document.getElementById('tabRanking');
  const tabContentCorr = document.getElementById('tabContentCorr');
  const tabContentRanking = document.getElementById('tabContentRanking');

  tabCorr.addEventListener('click', function () {
    tabContentCorr.classList.remove('hidden');
    tabContentRanking.classList.add('hidden');
    tabCorr.classList.replace('bg-gray-200', 'bg-blue-600');
    tabCorr.classList.replace('text-gray-700', 'text-white');
    tabRanking.classList.replace('bg-blue-600', 'bg-gray-200');
    tabRanking.classList.replace('text-white', 'text-gray-700');
  });

  tabRanking.addEventListener('click', function () {
    tabContentCorr.classList.add('hidden');
    tabContentRanking.classList.remove('hidden');
    tabRanking.classList.replace('bg-gray-200', 'bg-blue-600');
    tabRanking.classList.replace('text-gray-700', 'text-white');
    tabCorr.classList.replace('bg-blue-600', 'bg-gray-200');
    tabCorr.classList.replace('text-white', 'text-gray-700');
  });

  // 자산 조합 설정 모달 제어 요소
  const setAssetCombinationBtn = document.getElementById('setAssetCombinationBtn');
  const assetCombinationModal = document.getElementById('assetCombinationModal');
  const closeAssetCombinationModal = document.getElementById('closeAssetCombinationModal');
  const assetCombinationForm = document.getElementById('assetCombinationForm');
  
  const addComboStockBtn = document.getElementById('addComboStockBtn');
  const addComboStockModal = document.getElementById('addComboStockModal');
  const closeAddComboStockModal = document.getElementById('closeAddComboStockModal');
  const addComboStockForm = document.getElementById('addComboStockForm');
  const comboStockSearchInput = document.getElementById('comboStockSearch');
  const comboStockSearchResults = document.getElementById('comboStockSearchResults');
  
  // 상관관계 확인 버튼 및 표시 영역
  const checkCorrelationBtn = document.getElementById('checkCorrelationBtn');
  const correlationMatrixDiv = document.getElementById('correlationMatrix');
  const corrMatrixImage = document.getElementById('corrMatrixImage');
  
  // 자산 조합 데이터
  let comboTickers = [];
  let specificAssets = [];
  let selectedPeriod = '';
  
  // 특정 자산 체크박스
  const seoulAPTCheckbox = document.getElementById('seoulAPTCheckbox');
  const entireAPTCheckbox = document.getElementById('entireAPTCheckbox');
  
  // 자산 조합 설정 버튼 열기
  setAssetCombinationBtn.addEventListener('click', function () {
    assetCombinationModal.classList.remove('hidden');
    populateComboStockHoldings();
  });
  
  // 자산 조합 설정 모달 닫기
  closeAssetCombinationModal.addEventListener('click', function () {
    assetCombinationModal.classList.add('hidden');
    assetCombinationForm.reset();
    comboTickers = [];
    specificAssets = [];
    selectedPeriod = '';
    updateCheckCorrelationBtnState();
    clearCorrelationMatrix();
    populateComboStockHoldings();
  });
  
  // 종목 추가 모달 열기
  addComboStockBtn.addEventListener('click', function () {
    addComboStockModal.classList.remove('hidden');
  });
  
  // 종목 추가 모달 닫기
  closeAddComboStockModal.addEventListener('click', function () {
    addComboStockModal.classList.add('hidden');
    addComboStockForm.reset();
    comboStockSearchResults.classList.add('hidden');
  });
  
  // 종목 검색 (자산 조합 설정용)
  comboStockSearchInput.addEventListener('input', function () {
    const keyword = this.value.trim();
    if (keyword.length === 0) {
      comboStockSearchResults.innerHTML = '';
      comboStockSearchResults.classList.add('hidden');
      return;
    }
    
    fetch(`/api/search_ticker?keyword=${encodeURIComponent(keyword)}`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          comboStockSearchResults.innerHTML = `<li class="px-4 py-2">${data.error}</li>`;
          comboStockSearchResults.classList.remove('hidden');
          return;
        }
        
        if (data.results.length === 0) {
          comboStockSearchResults.innerHTML = '<li class="px-4 py-2">검색 결과가 없습니다.</li>';
          comboStockSearchResults.classList.remove('hidden');
          return;
        }
        
        comboStockSearchResults.innerHTML = '';
        data.results.forEach(item => {
          const li = document.createElement('li');
          li.className = 'px-4 py-2 hover:bg-gray-200 cursor-pointer';
          li.textContent = `${item.Symbol} - ${item.Name}`;
          li.addEventListener('click', function () {
            document.getElementById('comboStockSymbol').value = item.Symbol;
            comboStockSearchResults.innerHTML = '';
            comboStockSearchResults.classList.add('hidden');
          });
          comboStockSearchResults.appendChild(li);
        });
        comboStockSearchResults.classList.remove('hidden');
      })
      .catch(error => {
        console.error('Error:', error);
        comboStockSearchResults.innerHTML = '<li class="px-4 py-2">검색 중 오류가 발생했습니다.</li>';
        comboStockSearchResults.classList.remove('hidden');
      });
  });
  
  // 종목 추가 폼 제출 (자산 조합 설정용)
  addComboStockForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const symbol = document.getElementById('comboStockSymbol').value.trim();
    
    if (!symbol) {
      alert('종목을 선택해주세요.');
      return;
    }
    
    // 중복 종목 추가 방지
    if (comboTickers.includes(symbol)) {
      alert('이미 추가된 종목입니다.');
      return;
    }
    
    comboTickers.push(symbol);
    addComboStockModal.classList.add('hidden');
    addComboStockForm.reset();
    comboStockSearchResults.classList.add('hidden');
    populateComboStockHoldings();
    updateCheckCorrelationBtnState();
  });
  
  // 자산 조합 설정 폼 제출
  assetCombinationForm.addEventListener('submit', function (e) {
    e.preventDefault();
    
    // 선택된 특정 자산 수집
    specificAssets = [];
    if (seoulAPTCheckbox.checked) {
      specificAssets.push('SeoulAPT_Korea');
    }
    if (entireAPTCheckbox.checked) {
      specificAssets.push('entireAPT_Korea');
    }
    
    // 최근 기간 선택
    selectedPeriod = document.getElementById('recentPeriod').value;
    if (!selectedPeriod) {
      alert('최근 기간을 선택해주세요.');
      return;
    }
    
    // 전체 자산 조합 리스트
    const allTickers = [...comboTickers, ...specificAssets];
    
    if (allTickers.length === 0) {
      alert('적어도 하나의 종목을 추가해주세요.');
      return;
    }
    
    // 상관관계 확인 버튼 활성화
    checkCorrelationBtn.disabled = false;
    
    // 모달 닫기
    assetCombinationModal.classList.add('hidden');
  });
  
  // 특정 자산 체크박스 변경 시
  seoulAPTCheckbox.addEventListener('change', function () {
    if (this.checked && !comboTickers.includes(this.value)) {
      comboTickers.push(this.value);
      populateComboStockHoldings();
      updateCheckCorrelationBtnState();
    } else if (!this.checked && comboTickers.includes(this.value)) {
      comboTickers = comboTickers.filter(ticker => ticker !== this.value);
      populateComboStockHoldings();
      updateCheckCorrelationBtnState();
    }
  });
  
  entireAPTCheckbox.addEventListener('change', function () {
    if (this.checked && !comboTickers.includes(this.value)) {
      comboTickers.push(this.value);
      populateComboStockHoldings();
      updateCheckCorrelationBtnState();
    } else if (!this.checked && comboTickers.includes(this.value)) {
      comboTickers = comboTickers.filter(ticker => ticker !== this.value);
      populateComboStockHoldings();
      updateCheckCorrelationBtnState();
    }
  });
  
  // 자산 조합 보유 종목 표시 함수
  function populateComboStockHoldings() {
    const holdingsDiv = document.getElementById('comboStockHoldings');
    holdingsDiv.innerHTML = '';
    
    comboTickers.forEach(ticker => {
      const div = document.createElement('div');
      div.className = 'flex items-center justify-between p-2 border rounded';
      
      const info = document.createElement('span');
      info.textContent = `${ticker}`;
      
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600';
      deleteBtn.textContent = '삭제';
      deleteBtn.addEventListener('click', function () {
        removeTicker(ticker);
      });
      
      div.appendChild(info);
      div.appendChild(deleteBtn);
      holdingsDiv.appendChild(div);
    });
  }
  
  // 종목 삭제 함수
  function removeTicker(ticker) {
    comboTickers = comboTickers.filter(item => item !== ticker);
    // 특정 자산이라면 체크박스를 해제
    if (ticker === 'SeoulAPT_Korea') {
      seoulAPTCheckbox.checked = false;
    }
    if (ticker === 'entireAPT_Korea') {
      entireAPTCheckbox.checked = false;
    }
    populateComboStockHoldings();
    updateCheckCorrelationBtnState();
  }
  
  // 상관관계 확인 버튼 상태 업데이트 함수
  function updateCheckCorrelationBtnState() {
    if (comboTickers.length > 0 || specificAssets.length > 0) {
      // 사용자가 필요한 모든 정보를 입력했는지 확인
      if (selectedPeriod) {
        checkCorrelationBtn.disabled = false;
      }
    } else {
      checkCorrelationBtn.disabled = true;
    }
  }
  
  // 상관관계 확인 버튼 클릭 시
  checkCorrelationBtn.addEventListener('click', function () {
    const allTickers = [...comboTickers, ...specificAssets];
    
    // 데이터 전송
    fetch('/api/calculate_correlation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tickers: allTickers,
        period: selectedPeriod
      }),
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        alert(`오류: ${data.error}`);
      } else {
        displayCorrelationMatrix(data.image_url);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('상관관계 행렬을 계산하는 중 오류가 발생했습니다.');
    });
  });
  
  // 상관관계 행렬 이미지 표시 함수
  function displayCorrelationMatrix(imageUrl) {
    // 이미지 URL 설정
    corrMatrixImage.src = imageUrl;
    
    // 상관관계 행렬 표시 영역 보이기
    correlationMatrixDiv.classList.remove('hidden');
  }
  
  // 상관관계 행렬 초기화 함수
  function clearCorrelationMatrix() {
    correlationMatrixDiv.classList.add('hidden');
    corrMatrixImage.src = '';
  }
});