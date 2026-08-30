// 확장 전역 상수. 서비스 워커·팝업(모듈 컨텍스트)에서만 import 한다.
// 콘텐츠 스크립트는 모듈이 아니므로 필요한 값을 자체 선언한다.

export const API_BASE = 'http://localhost:8000';
export const WEBAPP_BASE = 'http://localhost:3000';

// 파츠 API 만 /api/v1 아래에 있다. 백엔드 현행 그대로 따른다.
export const PARTS_PREFIX = '/api/v1';

// 완성 프롬프트 총 길이 상한 (STRUCT-001·POL-101 참조).
export const MAX_PROMPT_LENGTH = 5000;

// 즐겨찾기 등록 상한 = 위젯 노출 수 (EXT §4.1.1).
export const MAX_FAVORITES = 5;

export const MSG = {
  GET_FAVORITES: 'PB_GET_FAVORITES',
  RENDER_PROMPT: 'PB_RENDER_PROMPT',
  OPEN_WEBAPP: 'PB_OPEN_WEBAPP',
  TRACK: 'PB_TRACK',
};

// 바가 그리는 상태 (EXT §4.2 상태별 화면).
export const STATE = {
  READY: 'READY',
  EMPTY: 'EMPTY',
  LOGIN_REQUIRED: 'LOGIN_REQUIRED',
  ERROR: 'ERROR',
};

// 에러 코드 — ERR-001 정본. 007 은 EXT §4.5 가 개발 배정으로 남긴 항목이라
// ERR-EXT-* 계열 다음 번호를 여기서 배정한다.
export const ERR = {
  NOT_READY: 'ERR-EXT-001',
  PARTIAL: 'ERR-EXT-002',
  NO_COMPOSER: 'ERR-EXT-003',
  LOAD_FAILED: 'ERR-EXT-004',
  LOGIN_REQUIRED: 'ERR-EXT-005',
  TAB_BLOCKED: 'ERR-EXT-006',
  LOCKED: 'ERR-EXT-007',
};

// 에러 코드 → 문구 키. 문구 자체는 _locales 에 있다 (EXT §4.5 구현 요청:
// 코드에 직접 쓰지 말고 한곳에 모을 것).
export const ERR_MESSAGE_KEY = {
  [ERR.NOT_READY]: 'errNotReady',
  [ERR.PARTIAL]: 'errPartial',
  [ERR.NO_COMPOSER]: 'errNoComposer',
  [ERR.LOAD_FAILED]: 'errLoadFailed',
  [ERR.LOGIN_REQUIRED]: 'errLoginRequired',
  [ERR.TAB_BLOCKED]: 'errTabBlocked',
  [ERR.LOCKED]: 'errLocked',
};
