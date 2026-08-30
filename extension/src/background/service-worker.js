// Prombutter service worker (MV3)
//
// 콘텐츠 스크립트는 LLM 사이트 오리진에서 돌기 때문에 백엔드를 직접 부르면
// 교차 출처 요청이 되고 인증 쿠키도 실리지 않는다. 그래서 네트워크는 전부 여기서 하고,
// 프롬프트 바는 메시지로만 대화한다.

import {
  ERR,
  MAX_FAVORITES,
  MAX_PROMPT_LENGTH,
  MSG,
  PARTS_PREFIX,
  STATE,
  WEBAPP_BASE,
} from '../shared/config.js';
import { apiFetch, UnauthorizedError } from '../shared/api.js';

const WORKSPACE_CACHE_KEY = 'workspaceId';
const EVENT_BUFFER_KEY = 'eventBuffer';
const EVENT_BUFFER_MAX = 200;

chrome.runtime.onInstalled.addListener(() => {
  console.info('[prombutter] installed');
});

// ---------------------------------------------------------------- 워크스페이스

// 워크스페이스는 계정당 1개로 고정이라 세션 스토리지에 캐시한다.
// 브라우저를 닫으면 사라지므로 계정을 바꿔도 남은 값이 따라오지 않는다.
async function getWorkspaceId() {
  const cached = await chrome.storage.session.get(WORKSPACE_CACHE_KEY);
  if (cached[WORKSPACE_CACHE_KEY]) return cached[WORKSPACE_CACHE_KEY];

  const workspace = await apiFetch('/workspaces');
  await chrome.storage.session.set({ [WORKSPACE_CACHE_KEY]: workspace.id });
  return workspace.id;
}

async function clearWorkspaceCache() {
  await chrome.storage.session.remove(WORKSPACE_CACHE_KEY);
}

// ---------------------------------------------------------------- 칩 메타 판정

// 칩은 누르기 전에 무슨 일이 일어날지 알려야 한다 (EXT §4.4 · §4.2.3).
// 그래서 목록을 받은 뒤 프롬프트마다 두 가지를 미리 판정한다.
//
//   hasVariables — 누르면 주입이 아니라 새 탭이 열린다
//   locked       — 삭제된 파츠를 참조해 쓸 수 없다 (EXT §4.2.2 · AC 8)
//
// 잠금은 백엔드가 알려주지 않는다. 프롬프트 상세의 PART 블록이 가리키는 파츠가
// 살아 있는 파츠 목록에 없으면 삭제된 것으로 본다.
async function loadActivePartIds(workspaceId) {
  const parts = await apiFetch(`${PARTS_PREFIX}/workspaces/${workspaceId}/parts`);
  return new Set(parts.map((part) => part.id));
}

async function describePrompt(workspaceId, prompt, activePartIds) {
  const [detail, variables] = await Promise.all([
    apiFetch(`/workspaces/${workspaceId}/prompts/${prompt.id}`),
    apiFetch(`/workspaces/${workspaceId}/prompts/${prompt.id}/variables`),
  ]);

  const locked = detail.blocks.some(
    (block) => block.block_type === 'PART' && block.part_id && !activePartIds.has(block.part_id),
  );

  return {
    id: prompt.id,
    title: prompt.title,
    hasVariables: variables.variables.length > 0,
    locked,
  };
}

// ---------------------------------------------------------------- 핸들러

async function handleGetFavorites() {
  const workspaceId = await getWorkspaceId();
  const favorites = await apiFetch(`/workspaces/${workspaceId}/prompts/favorites`);

  if (favorites.length === 0) return { state: STATE.EMPTY, prompts: [] };

  // 백엔드는 등록 최신순으로 준다. 칩 순서는 등록 시각 오름차순이 정본이라
  // (EXT §4.1.1) 여기서 뒤집는다.
  const ordered = [...favorites]
    .sort((a, b) => new Date(a.favorited_at) - new Date(b.favorited_at))
    .slice(0, MAX_FAVORITES);

  const activePartIds = await loadActivePartIds(workspaceId);
  const prompts = await Promise.all(
    ordered.map((prompt) => describePrompt(workspaceId, prompt, activePartIds)),
  );

  return { state: STATE.READY, prompts };
}

// 변수 없는 프롬프트만 여기까지 온다. 잠긴 프롬프트는 바에서 이미 막히지만,
// 목록을 받아둔 뒤 파츠가 지워졌을 수 있으므로 주입 직전에 한 번 더 본다.
async function handleRenderPrompt({ promptId }) {
  const workspaceId = await getWorkspaceId();

  const [detail, activePartIds] = await Promise.all([
    apiFetch(`/workspaces/${workspaceId}/prompts/${promptId}`),
    loadActivePartIds(workspaceId),
  ]);

  const locked = detail.blocks.some(
    (block) => block.block_type === 'PART' && block.part_id && !activePartIds.has(block.part_id),
  );
  if (locked) return { action: 'BLOCKED', errorCode: ERR.LOCKED };

  const { rendered, missing } = await apiFetch(
    `/workspaces/${workspaceId}/prompts/${promptId}/render`,
    { method: 'POST', body: { variables: {} } },
  );

  if (missing.length > 0) return { action: 'OPEN_WEBAPP', reason: 'HAS_VARIABLES' };
  if (rendered.length > MAX_PROMPT_LENGTH) {
    return { action: 'BLOCKED', errorCode: ERR.PARTIAL, length: rendered.length };
  }
  return { action: 'INJECT', rendered };
}

async function handleOpenWebapp({ path }) {
  // 확장이 만든 탭이라 팝업 차단에 걸리지 않는다. 그래도 실패하면 호출부가
  // ERR-EXT-006 을 띄운다.
  const url = new URL(path || '/', WEBAPP_BASE).toString();
  await chrome.tabs.create({ url });
  return {};
}

// EVENT-001 수집 엔드포인트가 백엔드에 아직 없다. 유실을 막기 위해 로컬에 쌓아두고,
// 엔드포인트가 생기면 이 버퍼를 그대로 비워 보낸다.
async function handleTrack({ event, params }) {
  const stored = await chrome.storage.local.get(EVENT_BUFFER_KEY);
  const buffer = stored[EVENT_BUFFER_KEY] || [];
  buffer.push({ event, params, device_type: 'extension', timestamp: new Date().toISOString() });
  await chrome.storage.local.set({ [EVENT_BUFFER_KEY]: buffer.slice(-EVENT_BUFFER_MAX) });
  return {};
}

const HANDLERS = {
  [MSG.GET_FAVORITES]: handleGetFavorites,
  [MSG.RENDER_PROMPT]: handleRenderPrompt,
  [MSG.OPEN_WEBAPP]: handleOpenWebapp,
  [MSG.TRACK]: handleTrack,
};

// ---------------------------------------------------------------- 메시지 배선

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const handler = HANDLERS[message?.type];
  if (!handler) {
    sendResponse({ ok: false, state: STATE.ERROR, errorCode: null });
    return false;
  }

  handler(message)
    .then((result) => sendResponse({ ok: true, ...result }))
    .catch(async (err) => {
      if (err instanceof UnauthorizedError) {
        await clearWorkspaceCache();
        sendResponse({ ok: false, state: STATE.LOGIN_REQUIRED, errorCode: ERR.LOGIN_REQUIRED });
        return;
      }
      console.warn('[prombutter] request failed', message.type, err);
      sendResponse({ ok: false, state: STATE.ERROR, errorCode: ERR.LOAD_FAILED });
    });

  return true; // 비동기 응답을 쓰므로 채널을 열어둔다.
});
