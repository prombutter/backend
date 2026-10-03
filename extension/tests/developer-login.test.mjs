import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const sourceBase = new URL('../src/', import.meta.url);
const encodeModule = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;

async function startWorker(apiBase = 'http://localhost:8000') {
  const configSource = (await readFile(new URL('shared/config.js', sourceBase), 'utf8'))
    .replace(/export const API_BASE = [^;]+;/, 'export const API_BASE = ' + JSON.stringify(apiBase) + ';');
  const configUrl = encodeModule(configSource);
  const apiSource = (await readFile(new URL('shared/api.js', sourceBase), 'utf8'))
    .replace("'./config.js'", JSON.stringify(configUrl));
  const apiUrl = encodeModule(apiSource);
  const workerSource = (await readFile(new URL('background/service-worker.js', sourceBase), 'utf8'))
    .replace("'../shared/config.js'", JSON.stringify(configUrl))
    .replace("'../shared/api.js'", JSON.stringify(apiUrl));
  const local = {};
  const session = { workspaceId: 'previous-account-workspace' };
  let listener;
  const storage = (values) => ({
    get: async (key) => ({ [key]: values[key] }),
    set: async (entries) => { Object.assign(values, entries); },
    remove: async (key) => { delete values[key]; },
  });
  globalThis.chrome = {
    permissions: { contains: async () => true },
    storage: { local: storage(local), session: storage(session) },
    runtime: {
      onInstalled: { addListener() {} },
      onMessage: { addListener(handler) { listener = handler; } },
    },
  };
  await import(`${encodeModule(workerSource)}#${crypto.randomUUID()}`);
  return {
    local,
    session,
    send: (type, params = {}) => new Promise((resolve) => {
      assert.equal(listener({ type, ...params }, {}, resolve), true);
    }),
  };
}

const jsonResponse = (status, body = { id: 'synthetic-developer-id' }) =>
  new Response(JSON.stringify(body), { status });

test('developer login confirms cookies, clears the old workspace and stores a safe event', async () => {
  const worker = await startWorker();
  const paths = [];
  globalThis.fetch = async (url, options) => {
    paths.push(new URL(url).pathname);
    assert.equal(options.credentials, 'include');
    if (url.endsWith('/auth/developer-login')) {
      assert.equal(options.method, 'POST');
      assert.equal(options.headers['X-Requested-With'], 'Prombutter-Extension');
    }
    return jsonResponse(200);
  };
  assert.equal((await worker.send('PB_DEVELOPER_LOGIN')).ok, true);
  assert.deepEqual(paths, ['/auth/developer-login', '/auth/me']);
  assert.equal(worker.session.workspaceId, undefined);
  const [event] = worker.local.eventBuffer;
  assert.equal(event.event, 'developer_login_result');
  assert.equal(event.params.result, 'success');
  assert.equal(event.params.reason, null);
  assert.equal(typeof event.params.request_id, 'string');
  assert.equal(typeof event.params.duration_ms, 'number');
  assert.match(event.timestamp, /Z$/);
  assert.deepEqual(Object.keys(event.params).sort(), ['duration_ms', 'reason', 'request_id', 'result']);
});

test('a remote API cannot be used for developer login', async () => {
  const worker = await startWorker('https://api.example.com');
  let calls = 0;
  globalThis.fetch = async () => { calls++; return jsonResponse(200); };
  const result = await worker.send('PB_DEVELOPER_LOGIN');
  assert.equal(result.ok, false);
  assert.equal(result.errorCode, 'ERR-EXT-009');
  assert.equal(calls, 0);
  assert.equal(worker.local.eventBuffer[0].params.result, 'blocked');
});

for (const status of [403, 404, 500]) {
  test(`HTTP ${status} preserves the failure result and records its classification`, async () => {
    const worker = await startWorker();
    globalThis.fetch = async () => jsonResponse(status, { error_code: `SYNTHETIC_${status}` });
    const result = await worker.send('PB_DEVELOPER_LOGIN');
    assert.equal(result.ok, false);
    assert.equal(result.errorCode, status === 500 ? 'ERR-EXT-008' : 'ERR-EXT-009');
    assert.equal(worker.local.eventBuffer[0].params.result, status === 500 ? 'failure' : 'blocked');
    assert.equal(worker.local.eventBuffer[0].params.reason, `SYNTHETIC_${status}`);
  });
}

test('missing authentication cookies fail without attempting refresh', async () => {
  const worker = await startWorker();
  const paths = [];
  globalThis.fetch = async (url) => {
    paths.push(new URL(url).pathname);
    return jsonResponse(url.endsWith('/auth/me') ? 401 : 200);
  };
  assert.equal((await worker.send('PB_DEVELOPER_LOGIN')).ok, false);
  assert.deepEqual(paths, ['/auth/developer-login', '/auth/me']);
  assert.equal(worker.local.eventBuffer[0].params.reason, 'SESSION_NOT_AVAILABLE');
});

test('an old account cookie cannot be mistaken for a developer session', async () => {
  const worker = await startWorker();
  globalThis.fetch = async (url) => jsonResponse(200, {
    id: url.endsWith('/auth/me') ? 'synthetic-old-account' : 'synthetic-developer-id',
  });
  const result = await worker.send('PB_DEVELOPER_LOGIN');
  assert.equal(result.ok, false);
  assert.equal(result.errorCode, 'ERR-EXT-008');
  assert.equal(worker.local.eventBuffer[0].params.reason, 'SESSION_USER_MISMATCH');
});

test('concurrent clicks issue one session and persist one event', async () => {
  const worker = await startWorker();
  let finishRequest;
  let loginCalls = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith('/auth/developer-login')) {
      loginCalls++;
      await new Promise((resolve) => { finishRequest = resolve; });
    }
    return jsonResponse(200);
  };
  const first = worker.send('PB_DEVELOPER_LOGIN');
  const second = worker.send('PB_DEVELOPER_LOGIN');
  await new Promise((resolve) => setImmediate(resolve));
  finishRequest();
  const results = await Promise.all([first, second]);
  assert.ok(results.every((result) => result.ok));
  assert.equal(loginCalls, 1);
  assert.equal(worker.local.eventBuffer.length, 1);
});

test('ordinary unauthenticated requests advertise the local developer button', async () => {
  const worker = await startWorker();
  globalThis.fetch = async () => jsonResponse(401);
  const result = await worker.send('PB_GET_FAVORITES');
  assert.equal(result.state, 'LOGIN_REQUIRED');
  assert.equal(result.developerLoginAvailable, true);
});

test('missing API permission is reported before fetching and stored for diagnosis', async () => {
  const worker = await startWorker('https://backend-prombutter-s-projects.vercel.app');
  let calls = 0;
  chrome.permissions.contains = async ({ origins }) => {
    assert.deepEqual(origins, ['https://backend-prombutter-s-projects.vercel.app/*']);
    return false;
  };
  globalThis.fetch = async () => { calls++; return jsonResponse(200); };
  const result = await worker.send('PB_GET_FAVORITES');
  assert.equal(result.state, 'ERROR');
  assert.equal(result.errorCode, 'ERR-EXT-010');
  assert.equal(calls, 0);
  const [event] = worker.local.eventBuffer;
  assert.equal(event.event, 'extension_api_access_result');
  assert.equal(event.params.reason, 'HOST_PERMISSION_MISSING');
  assert.match(event.timestamp, /Z$/);
});

test('network failures are classified and remain retryable', async () => {
  const worker = await startWorker();
  globalThis.fetch = async () => { throw new TypeError('synthetic network failure'); };
  assert.equal((await worker.send('PB_DEVELOPER_LOGIN')).ok, false);
  assert.equal(worker.local.eventBuffer[0].params.reason, 'NETWORK_ERROR');
  globalThis.fetch = async () => jsonResponse(200);
  assert.equal((await worker.send('PB_DEVELOPER_LOGIN')).ok, true);
  assert.equal(worker.local.eventBuffer.length, 2);
});

test('webapp account changes re-read the workspace instead of reusing an old owner', async () => {
  const worker = await startWorker();
  let account = 'first';
  const paths = [];
  globalThis.fetch = async (url) => {
    const path = new URL(url).pathname;
    paths.push(path);
    return jsonResponse(200, path === '/workspaces' ? { id: `${account}-workspace` } : []);
  };
  assert.equal((await worker.send('PB_GET_FAVORITES')).state, 'EMPTY');
  account = 'second';
  assert.equal((await worker.send('PB_GET_FAVORITES')).state, 'EMPTY');
  assert.deepEqual(paths, ['/workspaces', '/workspaces/first-workspace/prompts/favorites',
    '/workspaces', '/workspaces/second-workspace/prompts/favorites']);
});

test('concurrent diagnostic events are persisted without overwriting each other', async () => {
  const worker = await startWorker();
  chrome.storage.local.get = async (key) => structuredClone({ [key]: worker.local[key] });
  chrome.storage.local.set = async (entries) => {
    await new Promise((resolve) => setImmediate(resolve));
    Object.assign(worker.local, structuredClone(entries));
  };
  await Promise.all([worker.send('PB_TRACK', { event: 'first', params: {} }),
    worker.send('PB_TRACK', { event: 'second', params: {} })]);
  assert.deepEqual(worker.local.eventBuffer.map((event) => event.event), ['first', 'second']);
});

test('event storage failure preserves authentication and permits a later login', async () => {
  const worker = await startWorker();
  const originalWarning = console.warn;
  const originalSet = chrome.storage.local.set;
  const warnings = [];
  console.warn = (...message) => warnings.push(message);
  chrome.storage.local.set = async () => { throw new Error('synthetic quota failure'); };
  globalThis.fetch = async () => jsonResponse(200);
  try {
    assert.equal((await worker.send('PB_DEVELOPER_LOGIN')).ok, true);
    assert.equal(worker.local.eventBuffer, undefined);
    assert.equal(warnings.length, 1);
    assert.equal(warnings[0][0], '[prombutter] developer_login_result storage_failed');
    chrome.storage.local.set = originalSet;
    assert.equal((await worker.send('PB_DEVELOPER_LOGIN')).ok, true);
    assert.equal(worker.local.eventBuffer[0].params.result, 'success');
  } finally {
    console.warn = originalWarning;
    chrome.storage.local.set = originalSet;
  }
});
