// 팝업 문구는 하드코딩하지 않고 _locales 메시지를 쓴다.
const bind = (id, key) => {
  const el = document.getElementById(id);
  if (el) el.textContent = chrome.i18n.getMessage(key);
};

bind('popupTitle', 'extName');
bind('popupBody', 'popupBody');
