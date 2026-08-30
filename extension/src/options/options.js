const bind = (id, key, attr) => {
  const el = document.getElementById(id);
  if (!el) return;
  if (attr) el.setAttribute(attr, chrome.i18n.getMessage(key));
  else el.textContent = chrome.i18n.getMessage(key);
};

bind('logoLabel', 'extName', 'aria-label');
bind('optionsTitle', 'optionsTitle');
bind('optionsBody', 'optionsBody');
