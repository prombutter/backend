// 백엔드 호출 래퍼.
//
// 인증은 HttpOnly 쿠키(access_token / refresh_token)로 이뤄지므로 모든 요청에
// credentials: 'include' 를 붙인다. 확장이 대상 오리진에 host_permissions 를 가지면
// 크롬이 그 요청을 same-site 로 취급해 SameSite=Lax 쿠키를 함께 보낸다.
//
// 401 을 만나면 refresh 를 한 번만 시도하고 재요청한다. 재시도까지 실패하면
// UnauthorizedError 를 던져 호출부가 '로그인 필요' 상태로 내려가게 한다.

import { API_BASE } from './config.js';

export class UnauthorizedError extends Error {
  constructor() {
    super('UNAUTHORIZED');
    this.name = 'UnauthorizedError';
  }
}

export class ApiError extends Error {
  constructor(status, errorCode, message) {
    super(message || `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.errorCode = errorCode;
  }
}

// refresh 는 동시에 여러 번 날리지 않는다 — 토큰 회전이라 두 번째 요청이 폐기된 세션을
// 들고 가서 실패하고, 서버는 그것을 재사용 공격으로 본다.
let refreshInFlight = null;

async function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then((res) => res.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function parseError(res) {
  try {
    const body = await res.json();
    return new ApiError(res.status, body.error_code, body.message || body.detail);
  } catch {
    return new ApiError(res.status, null, null);
  }
}

export async function apiFetch(path, { method = 'GET', body } = {}, retry = true) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: 'include',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (res.status === 401) {
    if (retry && (await refreshSession())) {
      return apiFetch(path, { method, body }, false);
    }
    throw new UnauthorizedError();
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return null;
  return res.json();
}
