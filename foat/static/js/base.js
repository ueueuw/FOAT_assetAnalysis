// static/js/base.js

document.addEventListener('DOMContentLoaded', function () {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  const menuBtn = document.getElementById('openSidebarBtn');
  let isSidebarOpen = false;

  // 사이드바 토글 함수
  function toggleSidebar() {
    if (isSidebarOpen) {
      sidebar.classList.add('-translate-x-full');
      mainContent.classList.remove('ml-64');
      // 메뉴 아이콘 변경
      const menuIcon = menuBtn.querySelector('[data-lucide="x"]');
      if (menuIcon) {
        menuIcon.setAttribute('data-lucide', 'menu');
        lucide.createIcons();
      }
    } else {
      sidebar.classList.remove('-translate-x-full');
      mainContent.classList.add('ml-64');
      // X 아이콘으로 변경
      const menuIcon = menuBtn.querySelector('[data-lucide="menu"]');
      if (menuIcon) {
        menuIcon.setAttribute('data-lucide', 'x');
        lucide.createIcons();
      }
    }
    isSidebarOpen = !isSidebarOpen;
  }

  // 사이드바 외부 클릭 시 닫기
  document.addEventListener('click', function(event) {
    if (isSidebarOpen && 
        !sidebar.contains(event.target) && 
        !menuBtn.contains(event.target)) {
      toggleSidebar();
    }
  });

  // 이벤트 리스너 바인딩
  menuBtn.addEventListener('click', function(e) {
    e.stopPropagation(); // 이벤트 버블링 방지
    toggleSidebar();
  });

  // 스크롤 시 사이드바 위치 조정
  document.addEventListener('scroll', function() {
    if (isSidebarOpen) {
      sidebar.style.height = '100vh';
    }
  });
});