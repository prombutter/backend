// 웹 앱 도메인에 익스텐션 설치 표식을 남긴다 (기획서 4.3.1).
// 웹 앱은 MutationObserver 로 이 속성을 감지해 설치 유도 배너를 숨긴다.

const INSTALL_ATTRIBUTE = 'data-promptbutter-ext';

function markInstalled() {
  document.documentElement.setAttribute(INSTALL_ATTRIBUTE, 'installed');
}

markInstalled();
document.addEventListener('DOMContentLoaded', markInstalled, { once: true });
