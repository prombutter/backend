// EXT-WIDGET 프롬프트 바 — ChatGPT·Claude 입력창 바로 위 고정 (EXT §4.2).
//
// 남의 서비스 화면에 끼어드는 UI 라 §4.4 보호 기준이 일반 화면보다 엄격하다.
// 전면 오버레이·드래그·이탈 방해가 없고, 주입은 기존 입력을 지우지 않는다.
//
// 콘텐츠 스크립트는 모듈이 아니라서 shared/ 를 import 할 수 없다. 메시지 타입과
// 에러 코드는 여기서 다시 선언하고, 백엔드 호출은 전부 서비스 워커에 맡긴다.

(() => {
  'use strict';

  const MSG = {
    GET_FAVORITES: 'PB_GET_FAVORITES',
    RENDER_PROMPT: 'PB_RENDER_PROMPT',
    OPEN_WEBAPP: 'PB_OPEN_WEBAPP',
    TRACK: 'PB_TRACK',
  };

  const ERR = {
    NOT_READY: 'ERR-EXT-001',
    PARTIAL: 'ERR-EXT-002',
    NO_COMPOSER: 'ERR-EXT-003',
    LOAD_FAILED: 'ERR-EXT-004',
    LOGIN_REQUIRED: 'ERR-EXT-005',
    TAB_BLOCKED: 'ERR-EXT-006',
    LOCKED: 'ERR-EXT-007',
  };

  // 문구는 코드에 직접 쓰지 않는다 (EXT §4.5 구현 요청). 여기는 코드→키 지도만 둔다.
  const ERR_MESSAGE_KEY = {
    [ERR.NOT_READY]: 'errNotReady',
    [ERR.PARTIAL]: 'errPartial',
    [ERR.NO_COMPOSER]: 'errNoComposer',
    [ERR.LOAD_FAILED]: 'errLoadFailed',
    [ERR.LOGIN_REQUIRED]: 'errLoginRequired',
    [ERR.TAB_BLOCKED]: 'errTabBlocked',
    [ERR.LOCKED]: 'errLocked',
  };

  // 웹 앱 화면 경로. 프론트엔드 라우팅이 바뀌면 여기만 고치면 된다.
  const ROUTES = {
    LOGIN: '/login',
    PROMPTS: '/prompts',
    NEW_PROMPT: '/prompts/new',
    PROMPT: (id) => '/prompts/' + id,
  };

  const BAR_ID = 'prombutter-bar';
  const TITLE_MAX = 15; // 칩 제목 표시 기준 (EXT §4.2 레이아웃)

  const t = (key) => chrome.i18n.getMessage(key) || key;
  const send = (message) => chrome.runtime.sendMessage(message);
  const track = (event, params) => send({ type: MSG.TRACK, event, params }).catch(() => {});

  // ------------------------------------------------------------ 사이트 어댑터
  //
  // 지원 도메인은 chatgpt.com·claude.ai·gemini.google.com 이다. 구 chat.openai.com 은
  // 쓰지 않는다 (EXT §4.2.1). 세 사이트 모두 입력창이 contenteditable 이고 DOM 이 자주
  // 바뀌므로, 후보를 모아 가시성 점수로 고른다.

  const ADAPTERS = [
    {
      test: (host) => host === 'chatgpt.com',
      // 우선 후보 → 폭넓은 후보 순. 뒤엣것은 숨은 모바일 입력창까지 걸리므로
      // 아래 점수 매기기로 걸러낸다.
      composerSelectors: [
        '#prompt-textarea',
        'form div[contenteditable="true"]',
        'form textarea',
        'div[contenteditable="true"]',
        'textarea',
      ],
    },
    {
      test: (host) => host === 'claude.ai',
      composerSelectors: [
        'div[contenteditable="true"].ProseMirror',
        'fieldset div[contenteditable="true"]',
        'div[contenteditable="true"]',
        'textarea',
      ],
    },
    {
      // Gemini 는 Quill 편집기를 쓴다.
      test: (host) => host === 'gemini.google.com',
      composerSelectors: [
        'rich-textarea div.ql-editor[contenteditable="true"]',
        'div.ql-editor[contenteditable="true"]',
        'rich-textarea div[contenteditable="true"]',
        'div[contenteditable="true"]',
        'textarea',
      ],
    },
  ];

  const adapter = ADAPTERS.find((a) => a.test(location.hostname));
  if (!adapter) return;

  // 실제로 사용자가 쓰는 입력창인지 본다.
  //
  // 선택자를 순서대로 훑어 처음 걸리는 것을 쓰면 안 된다. ChatGPT 는 데스크톱 입력창과
  // 별개로 숨은 모바일 입력창(mobile-composer-prompt)을 문서에 함께 두고, 그쪽이 먼저
  // 걸리면 바가 화면 밖 컨테이너에 붙어 아무것도 보이지 않는다.
  function scoreCandidate(el) {
    if (!(el instanceof HTMLElement)) return -1;
    if (el.closest('[aria-hidden="true"]')) return -1;
    if (el.getAttribute('aria-hidden') === 'true') return -1;

    const rect = el.getBoundingClientRect();
    if (rect.width < 180 || rect.height < 20) return -1; // 접혔거나 숨은 것
    // 화면 안에 걸쳐 있어야 한다. 뷰포트 밖으로 밀어둔 입력창은 쓰지 않는다.
    if (rect.bottom <= 0 || rect.top >= window.innerHeight) return -1;
    if (rect.right <= 0 || rect.left >= window.innerWidth) return -1;

    const style = window.getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') return -1;
    if (parseFloat(style.opacity) === 0) return -1;

    // 넓고 아래쪽에 있는 것이 대화 입력창일 확률이 높다.
    return rect.width * rect.height + rect.top;
  }

  // 매 변경마다 전수 스캔하면 getBoundingClientRect·getComputedStyle 가 강제 레이아웃을
  // 일으킨다. ChatGPT 처럼 무거운 DOM 에서는 이것만으로 탭이 버벅이거나 죽는다.
  // 그래서 한 번 고른 입력창을 기억하고, 그것이 살아 있고 여전히 쓸 만하면 그대로 쓴다.
  let composerCache = null;

  function currentComposer() {
    if (composerCache?.isConnected && scoreCandidate(composerCache) > 0) return composerCache;
    composerCache = findComposer();
    return composerCache;
  }

  function findComposer() {
    let best = null;
    let bestScore = -1;

    for (const selector of adapter.composerSelectors) {
      for (const el of document.querySelectorAll(selector)) {
        const score = scoreCandidate(el);
        if (score > bestScore) {
          bestScore = score;
          best = el;
        }
      }
      // 앞선 선택자에서 쓸 만한 것을 찾았으면 더 넓은 후보로 내려가지 않는다.
      if (best) break;
    }
    return best;
  }

  // 입력창 자체가 아니라 그것을 감싼 블록 위에 바를 놓아야 레이아웃이 덜 깨진다.
  function findAnchor(composer) {
    return composer.closest('form') || composer.parentElement;
  }

  // ------------------------------------------------------------ 주입
  //
  // 이어붙이기가 원칙이다 (EXT §4.2.2). 쓰던 글이 클릭 한 번에 사라지면 되돌릴 수 없고,
  // 잘못 붙은 텍스트는 지우면 그만이라 덜 위험한 쪽을 택한다.

  const readText = (composer) =>
    composer.value !== undefined ? composer.value : composer.textContent;

  // 기존 내용과 새 프롬프트 사이에 빈 줄 하나를 둔다. 이미 빈 줄로 끝나면 더 넣지 않는다.
  function separatorFor(existing) {
    if (existing.length === 0) return '';
    if (/\n[ \t]*\n[ \t]*$/.test(existing)) return '';
    if (/\n[ \t]*$/.test(existing)) return '\n';
    return '\n\n';
  }

  // 주입 성공 판정 — 입력창 전체를 프롬프트와 비교할 수 없다. 기존 내용이 앞에 있어
  // 항상 불일치가 되고, "어딘가 들어 있는가" 로만 보면 사용자가 이미 같은 문장을 쓰던
  // 경우와 구분되지 않는다. 그래서 주입 전 길이를 기억해 두고 늘어난 만큼만 확인한다.
  // 공백을 지우고 비교하는 이유는 ProseMirror 가 줄바꿈을 문단으로 바꾸면서
  // textContent 의 개행이 사라지기 때문이다 — 개행 유무로 실패를 오판하면
  // ERR-EXT-002 가 정상 주입을 전부 실패로 기록한다.
  const squeeze = (s) => s.replace(/\s+/g, '');

  function verifyInjection(before, after, text) {
    const b = squeeze(before);
    const a = squeeze(after);
    const x = squeeze(text);
    if (x.length === 0) return true;
    return a.length - b.length >= x.length && a.endsWith(x);
  }

  function insertIntoComposer(composer, payload) {
    composer.focus();

    if (composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement) {
      // React 는 값을 직접 대입하면 내부 상태가 따라오지 않아 네이티브 setter 를 쓴다.
      const descriptor = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(composer),
        'value',
      );
      const next = composer.value + payload;
      if (descriptor?.set) descriptor.set.call(composer, next);
      else composer.value = next;
      composer.dispatchEvent(new Event('input', { bubbles: true }));
      composer.setSelectionRange(next.length, next.length); // 커서는 주입된 끝에
      return;
    }

    // contenteditable 은 execCommand 로 넣어 편집기가 자기 트랜잭션으로 처리하게 한다.
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(composer);
    range.collapse(false); // 커서를 맨 끝으로 — 이어붙이기라 항상 끝에서 시작한다
    selection.removeAllRanges();
    selection.addRange(range);

    if (!document.execCommand('insertText', false, payload)) {
      const data = new DataTransfer();
      data.setData('text/plain', payload);
      composer.dispatchEvent(
        new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true }),
      );
    }
  }

  // 새로 들어온 부분의 시작 지점이 보이도록 스크롤한다 (EXT §4.2.2).
  // 긴 글을 쓰던 중이면 아래에 붙은 프롬프트가 화면 밖이라 아무 일도 없었던 것처럼 보인다.
  // 커서는 끝에 둔 채 스크롤 위치만 손대므로 바로 이어 쓰거나 전송할 수 있다.
  function revealInsertionStart(composer, linesBefore) {
    if (composer.scrollHeight <= composer.clientHeight) return; // 이미 다 보인다

    const style = window.getComputedStyle(composer);
    const lineHeight =
      parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.5 || 20;
    // 줄바꿈 문자 기준 근사치다. 자동 줄바꿈까지 세지는 않지만 시작 지점을 화면 안으로
    // 들여놓는 목적에는 충분하다.
    const target = Math.max(0, linesBefore * lineHeight - lineHeight);
    composer.scrollTop = Math.min(target, composer.scrollHeight - composer.clientHeight);
  }

  // ------------------------------------------------------------ 바 UI

  let bar = null; // { host, chipsEl, statusEl }
  let data = null; // { state, prompts }

  const truncate = (title) =>
    title.length > TITLE_MAX ? title.slice(0, TITLE_MAX) + '…' : title;

  // 안내는 칩 위에 겹쳐 띄운다. 자리를 따로 잡으면 바가 그만큼 두꺼워져 LLM 화면의
  // 인사말까지 침범하고, 그렇다고 나타날 때 칩을 밀어내면 입력창 위치가 흔들린다.
  // 겹치기는 둘 다 피한다 (EXT §4.3.2 디자인 확인 사항).
  let dismissStatus = null;

  function setStatus(text, { action, transient = false } = {}) {
    const { statusEl, root } = bar;

    if (dismissStatus) {
      root.removeEventListener('pointerdown', dismissStatus, true);
      root.removeEventListener('keydown', dismissStatus, true);
      dismissStatus = null;
    }

    statusEl.replaceChildren(document.createTextNode(text || ''));
    statusEl.classList.toggle('pb-status-empty', !text);

    if (action) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'pb-link';
      button.textContent = action.label;
      button.addEventListener('click', action.onClick);
      button.addEventListener('keydown', onItemKeydown);
      statusEl.append(' ', button);
    }

    // 주입 성공·실패 같은 일시적 안내는 칩을 가린 채로 남으면 안 된다.
    // 다음 조작에서 걷어내고 칩을 되돌려 준다. 상태 안내(로그인 필요·빈 목록)는 남긴다.
    if (text && transient) {
      dismissStatus = (event) => {
        if (event.target.closest?.('.pb-link')) return;
        setStatus('');
      };
      root.addEventListener('pointerdown', dismissStatus, true);
      root.addEventListener('keydown', dismissStatus, true);
    }

    resetRoving();
  }

  function showError(code) {
    setStatus(t(ERR_MESSAGE_KEY[code] || 'errLoadFailed'), { transient: true });
  }

  // 바 전체가 하나의 정거장이다 (EXT §4.4.2). 칩·[+]·안내 속 버튼을 한 그룹으로 묶어야
  // 바를 쓰지 않는 사람이 탭 두 번으로 입력창에 닿는다. 그룹 안에서는 방향키로 옮겨 다닌다.
  const barItems = () =>
    Array.from(bar.chipsEl.querySelectorAll('.pb-chip'))
      .concat(Array.from(bar.statusEl.querySelectorAll('.pb-link')))
      .concat(bar.plusEl);

  // 그룹에서 탭으로 들어오는 문은 하나만 열어 둔다.
  function resetRoving() {
    barItems().forEach((item, i) => {
      item.tabIndex = i === 0 ? 0 : -1;
    });
  }

  function moveFocus(nextIndex) {
    const items = barItems();
    items.forEach((item, i) => {
      item.tabIndex = i === nextIndex ? 0 : -1;
    });
    items[nextIndex]?.focus();
  }

  function onItemKeydown(event) {
    const chips = barItems();
    const index = chips.indexOf(event.currentTarget);
    if (index < 0) return;

    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      const delta = event.key === 'ArrowRight' ? 1 : -1;
      moveFocus((index + delta + chips.length) % chips.length);
      return;
    }
    if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      moveFocus(event.key === 'Home' ? 0 : chips.length - 1);
      return;
    }
    // 언제든 한 번에 입력창으로 빠져나올 수 있어야 한다 (EXT §4.4.2).
    if (event.key === 'Escape') {
      event.preventDefault();
      // 캐시해 두면 SPA 리렌더 뒤에 떨어져 나간 노드를 가리킨다. 쓸 때마다 찾는다.
      currentComposer()?.focus();
    }
  }

  function buildChip(prompt, index) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'pb-chip';
    chip.tabIndex = index === 0 ? 0 : -1;
    chip.addEventListener('keydown', onItemKeydown);

    const label = document.createElement('span');
    label.className = 'pb-chip-label';
    label.textContent = truncate(prompt.title);
    chip.append(label);

    // 화면에서 줄여 보이더라도 전체 제목이 읽혀야 한다 (EXT §4.4.3).
    let spoken = prompt.title;

    if (prompt.locked) {
      // 비활성을 색으로만 구분하지 않는다 (EXT §4.2·§4.4.4). 표시를 하나 붙이되
      // 포커스는 남겨 둔다 — 못 쓰는 이유를 들을 수 있어야 하기 때문이다.
      chip.append(buildMark('⊘', 'pb-mark-locked'));
      chip.classList.add('pb-chip-locked');
      chip.setAttribute('aria-disabled', 'true');
      chip.title = t('errLocked');
      spoken += ', ' + t('a11yLocked');
    } else if (prompt.hasVariables) {
      // 누르기 전에 새 탭이 열릴 것을 알아야 한다 (EXT §4.2.3).
      chip.append(buildMark('↗', 'pb-mark-external'));
      chip.title = t('tooltipHasVariables');
      spoken += ', ' + t('a11yOpensNewTab');
    }

    chip.setAttribute('aria-label', spoken);
    chip.addEventListener('click', () => usePrompt(prompt, chip));
    return chip;
  }

  function buildMark(glyph, className) {
    const mark = document.createElement('span');
    mark.className = 'pb-mark ' + className;
    mark.setAttribute('aria-hidden', 'true');
    mark.textContent = glyph;
    return mark;
  }

  function render() {
    if (!bar) return;
    const { chipsEl } = bar;

    if (!data) {
      chipsEl.replaceChildren();
      setStatus(t('statusLoading'));
      return;
    }
    if (data.state === 'LOGIN_REQUIRED') {
      chipsEl.replaceChildren();
      setStatus(t('errLoginRequired'), {
        action: { label: t('actionLogin'), onClick: () => openWebapp(ROUTES.LOGIN) },
      });
      return;
    }
    if (data.state === 'EMPTY') {
      chipsEl.replaceChildren();
      setStatus(t('statusEmpty'), {
        action: { label: t('actionOpenWebapp'), onClick: () => openWebapp(ROUTES.PROMPTS) },
      });
      return;
    }
    if (data.state !== 'READY') {
      chipsEl.replaceChildren();
      setStatus(t('errLoadFailed'), {
        action: { label: t('actionRetry'), onClick: () => loadFavorites(true) },
      });
      return;
    }

    chipsEl.replaceChildren(...data.prompts.map(buildChip));
    setStatus(''); // setStatus 가 로빙을 다시 잡는다
  }

  // ------------------------------------------------------------ 데이터

  let inFlight = null;

  async function loadFavorites(force = false) {
    if (inFlight && !force) return inFlight;

    data = null;
    render(); // 바는 이미 보인 채로 칩 자리에만 로딩을 그린다 (EXT §4.2 상태별 화면)

    inFlight = send({ type: MSG.GET_FAVORITES })
      .catch(() => null)
      .then((res) => {
        if (!res) return { state: 'ERROR' };
        if (!res.ok) return { state: res.state === 'LOGIN_REQUIRED' ? 'LOGIN_REQUIRED' : 'ERROR' };
        return { state: res.state, prompts: res.prompts };
      })
      .finally(() => {
        inFlight = null;
      });

    data = await inFlight;
    render();
    return data;
  }

  // ------------------------------------------------------------ 동작

  async function openWebapp(path) {
    const res = await send({ type: MSG.OPEN_WEBAPP, path }).catch(() => null);
    if (res?.ok) {
      track('open_webapp_tab', { path });
      return true;
    }
    showError(ERR.TAB_BLOCKED);
    track('open_webapp_tab_fail', { path, error_code: ERR.TAB_BLOCKED });
    return false;
  }

  async function usePrompt(prompt, chip) {
    // 잠긴 프롬프트는 눌러도 주입하지 않는다 (EXT §4.2.2 · AC 8).
    if (prompt.locked) {
      showError(ERR.LOCKED);
      return;
    }

    // 변수가 있으면 주입이 아니라 웹 앱으로 보낸다 (EXT §4.2.3).
    if (prompt.hasVariables) {
      await openWebapp(ROUTES.PROMPT(prompt.id));
      return;
    }

    chip.disabled = true;
    track('prompt_inject_attempt', { prompt_id: prompt.id, entrypoint: 'ext_entry' });

    try {
      const res = await send({ type: MSG.RENDER_PROMPT, promptId: prompt.id });

      if (!res.ok) {
        if (res.state === 'LOGIN_REQUIRED') {
          data = { state: 'LOGIN_REQUIRED' };
          render();
          return;
        }
        throw new Error(res.errorCode || ERR.LOAD_FAILED);
      }
      if (res.action === 'OPEN_WEBAPP') {
        await openWebapp(ROUTES.PROMPT(prompt.id));
        return;
      }
      if (res.action === 'BLOCKED') {
        showError(res.errorCode);
        track('prompt_inject_fail', { prompt_id: prompt.id, error_code: res.errorCode });
        return;
      }

      const composer = currentComposer();
      if (!composer) throw new Error(ERR.NO_COMPOSER);

      const before = readText(composer);
      insertIntoComposer(composer, separatorFor(before) + res.rendered);

      const after = readText(composer);
      if (!verifyInjection(before, after, res.rendered)) throw new Error(ERR.PARTIAL);

      revealInsertionStart(composer, before.split('\n').length - 1);
      // 화면을 보지 않는 사용자에게는 이어붙이기가 더욱 티가 나지 않는다 (EXT §4.4.3).
      setStatus(t('statusInjected'), { transient: true });
      track('prompt_inject_success', {
        prompt_id: prompt.id,
        prompt_length: res.rendered.length,
        entrypoint: 'ext_entry',
      });
    } catch (err) {
      const code = Object.values(ERR).includes(err.message) ? err.message : ERR.NOT_READY;
      showError(code); // 안내는 바 안에만 — Toast 는 원래 사이트를 가린다 (EXT §4.3.2)
      track('prompt_inject_fail', { prompt_id: prompt.id, error_code: code });
    } finally {
      chip.disabled = false;
    }
  }

  // ------------------------------------------------------------ 부착

  // 폰트는 문서 단위로만 등록된다 — Shadow DOM 안에 넣은 @font-face 는 무시되므로
  // 정의만 호스트 문서 head 에 심는다. 이 시트에는 @font-face 밖에 없어서 호스트
  // 페이지의 다른 요소를 건드리지 않는다. 호스트 CSP 가 막으면 조용히 실패하고
  // 시스템 폰트로 내려간다.
  const FONT_LINK_ID = 'prombutter-font';

  function ensureFont() {
    if (document.getElementById(FONT_LINK_ID)) return;
    const link = document.createElement('link');
    link.id = FONT_LINK_ID;
    link.rel = 'stylesheet';
    link.href = chrome.runtime.getURL('styles/pretendard.css');
    (document.head || document.documentElement).append(link);
  }

  function buildBar(anchor) {
    ensureFont();
    const host = document.createElement('div');
    host.id = BAR_ID;
    const shadow = host.attachShadow({ mode: 'open' });

    // 토큰을 먼저, 그것을 쓰는 규칙을 나중에. 순서가 바뀌면 var() 가 빈 값이 된다.
    for (const href of ['styles/tokens.css', 'styles/widget.css']) {
      const style = document.createElement('link');
      style.rel = 'stylesheet';
      style.href = chrome.runtime.getURL(href);
      shadow.append(style);
    }

    const root = document.createElement('div');
    root.className = 'pb-bar';
    root.setAttribute('role', 'toolbar');
    // 원래 사이트가 아니라 PromButter 가 넣은 도구임을 알린다 (EXT §4.4.3).
    root.setAttribute('aria-label', t('barLabel'));

    // 워드마크는 CSS 배경으로 넣는다. 테마에 따라 남색·크림 두 벌이 갈리는데,
    // 그 판단을 토큰에 맡기면 여기서 테마를 알 필요가 없다.
    const mark = document.createElement('span');
    mark.className = 'pb-brand';
    mark.setAttribute('role', 'img');
    mark.setAttribute('aria-label', t('extName'));

    const chipsEl = document.createElement('div');
    chipsEl.className = 'pb-chips';

    const plusEl = document.createElement('button');
    plusEl.type = 'button';
    plusEl.className = 'pb-plus';
    plusEl.textContent = '+';
    plusEl.setAttribute('aria-label', t('a11yNewPrompt'));
    plusEl.title = t('actionNewPrompt');
    plusEl.addEventListener('click', () => openWebapp(ROUTES.NEW_PROMPT));
    plusEl.addEventListener('keydown', onItemKeydown);

    // 안내 줄은 항상 자리를 차지한다. 나타날 때 칩을 밀어내면 입력창 위치가 흔들린다
    // (EXT §4.3.2 디자인 확인 사항).
    const statusEl = document.createElement('p');
    statusEl.className = 'pb-status pb-status-empty';
    statusEl.setAttribute('role', 'status');
    statusEl.setAttribute('aria-live', 'polite');

    root.append(mark, chipsEl, plusEl, statusEl);
    shadow.append(root);

    bar = { host, root, chipsEl, statusEl, plusEl };
    anchor.parentElement.insertBefore(host, anchor);
  }

  let anchorRef = null;

  // 자리다툼 차단기.
  //
  // 호스트가 React 면 그쪽도 같은 컨테이너를 다시 그리며 우리 노드를 걷어낸다.
  // 우리가 그때마다 되넣으면 그 삽입이 또 변경으로 잡혀 서로 무한히 밀고 당긴다.
  // 그 상태가 되면 탭이 CPU 를 다 쓰고 죽으므로, 짧은 시간에 재부착이 몰리면
  // 손을 뗀다. 바가 사라지는 편이 브라우저가 멎는 것보다 낫다.
  const REATTACH_WINDOW_MS = 10000;
  const REATTACH_LIMIT = 20;
  let reattachTimes = [];
  let surrendered = false;

  function mayReattach() {
    const now = Date.now();
    reattachTimes = reattachTimes.filter((t) => now - t < REATTACH_WINDOW_MS);
    if (reattachTimes.length >= REATTACH_LIMIT) {
      surrendered = true;
      observer.disconnect();
      console.warn('[prombutter] 호스트 페이지와 자리다툼이 감지되어 프롬프트 바 재부착을 멈춥니다.');
      return false;
    }
    reattachTimes.push(now);
    return true;
  }

  function mount() {
    if (surrendered) return;

    // 빠른 경로 — 이미 제자리에 있으면 아무것도 재지 않는다. 여기서 걸러야
    // 대부분의 DOM 변경이 레이아웃 계산 없이 끝난다.
    if (bar?.host.isConnected && anchorRef?.isConnected && bar.host.nextElementSibling === anchorRef) {
      return;
    }

    const composer = currentComposer();
    if (!composer) return;

    const anchor = findAnchor(composer);
    if (!anchor?.parentElement) return;

    // 바가 살아 있어도 입력창이 교체됐으면 새 입력창 위로 옮긴다. ChatGPT·Claude 는
    // 하이드레이션·라우팅에서 입력창 노드를 통째로 갈아끼우고, 그때 바만 남으면
    // 엉뚱한 자리에 떠 있게 된다.
    if (bar?.host.isConnected) {
      if (bar.host.nextElementSibling !== anchor) {
        if (!mayReattach()) return;
        anchor.parentElement.insertBefore(bar.host, anchor);
      }
      anchorRef = anchor;
      observeFrom(anchor.parentElement);
      return;
    }
    if (anchor.parentElement.querySelector('#' + BAR_ID)) return;
    if (!mayReattach()) return;

    buildBar(anchor);
    anchorRef = anchor;
    observeFrom(anchor.parentElement);
    // 사이트 구조가 바뀌어 엉뚱한 곳에 붙었을 때 눈으로 확인할 단서를 남긴다.
    console.debug('[prombutter] 프롬프트 바 부착', composer);
    render(); // 로딩 상태의 바를 먼저 세운다
    loadFavorites();
  }

  // 로그인은 다른 탭에서 끝난다. 돌아왔을 때 새로고침을 요구하면 쓰던 입력이 날아가므로
  // 탭이 다시 보이는 순간 상태만 다시 확인한다 (EXT §4.2.4).
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState !== 'visible') return;
    if (!bar?.host.isConnected) return;
    if (data?.state !== 'LOGIN_REQUIRED') return;

    const next = await loadFavorites(true);
    if (next?.state === 'READY' || next?.state === 'EMPTY') {
      setStatus(t('statusSignedIn'));
    }
  });

  // 두 사이트 모두 SPA 라 라우팅·리렌더로 입력창이 통째로 교체된다.
  // 바가 떨어져 나가면 다시 붙인다.
  // 관찰 범위를 좁히는 것이 핵심이다.
  //
  // 문서 전체를 subtree 로 감시하면 LLM 이 답변을 흘려보내는 동안 초당 수백~수천 건의
  // 변경이 우리 콜백까지 올라온다. 우리가 그 기록을 쓰지 않아도 브라우저는 매번 기록을
  // 만들어야 하고, 그 비용이 호스트 페이지의 렌더링과 겹치면 탭이 버틸 수 없다.
  //
  // 그래서 입력창을 찾을 때까지만 문서 전체를 보고, 바를 붙인 뒤에는 바가 놓인 그 자리만
  // 본다. 대화 영역이 아무리 바뀌어도 우리 콜백은 조용하다. 그 좁은 자리가 통째로
  // 사라지는 경우(라우팅·전면 리렌더)는 아래 느린 점검이 잡는다.
  const MOUNT_DEBOUNCE_MS = 250;
  const FALLBACK_CHECK_MS = 2000;
  let mountTimer = null;
  let observedRoot = null;

  function scheduleMount() {
    if (mountTimer || surrendered) return;
    mountTimer = setTimeout(() => {
      mountTimer = null;
      if (document.visibilityState === 'visible') mount();
    }, MOUNT_DEBOUNCE_MS);
  }

  const observer = new MutationObserver(scheduleMount);

  function observeFrom(root) {
    if (observedRoot === root || surrendered) return;
    observer.disconnect();
    observedRoot = root;
    observer.observe(
      root,
      root === document.body ? { childList: true, subtree: true } : { childList: true },
    );
  }

  // 좁게 보는 동안 그 자리 자체가 사라졌는지만 이따금 확인한다. isConnected 두 번이라
  // 비용이 거의 없다.
  setInterval(() => {
    if (surrendered || document.visibilityState !== 'visible') return;
    if (bar?.host.isConnected && anchorRef?.isConnected) return;
    observeFrom(document.body);
    mount();
  }, FALLBACK_CHECK_MS);

  observeFrom(document.body);
  mount();
})();
