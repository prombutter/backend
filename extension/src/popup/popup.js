// 팝업 문구는 하드코딩하지 않고 _locales 메시지를 쓴다.
const bind = (id, key, attr) => {
  const el = document.getElementById(id);
  if (!el) return;
  if (attr) el.setAttribute(attr, chrome.i18n.getMessage(key));
  else el.textContent = chrome.i18n.getMessage(key);
};

bind('logoLabel', 'extName', 'aria-label');
bind('popupTitle', 'extName');
bind('popupBody', 'popupBody');
