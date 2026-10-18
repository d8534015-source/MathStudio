(() => {
  const build = '__BUILD_ID__';
  const errors = [];
  const text = value => {
    if (!value) return 'Unknown browser error';
    if (value instanceof Error) return value.stack || value.message || String(value);
    return String(value);
  };
  window.addEventListener('error', event => {
    errors.push(event.message || text(event.error));
  }, true);
  window.addEventListener('unhandledrejection', event => {
    errors.push(text(event.reason));
  });
  window.setTimeout(() => {
    if (window.__MATHSTUDIO_SCRIPT_STARTED__) return;
    const app = document.getElementById('app');
    if (!app) return;
    const detail = errors.length ? errors.join('\n') : 'The main JavaScript module did not start. Try Ctrl+Shift+R once, then copy the message below if it remains.';
    app.innerHTML = '<section class="panel auth"><p class="eyebrow" data-i18n="diagnostics.label">Startup diagnostic</p><h1 data-i18n="diagnostics.title">Math Studio could not open</h1><p data-i18n="diagnostics.body">The server page loaded, but the app JavaScript did not start.</p><pre id="startup-detail" data-no-translate style="white-space:pre-wrap;overflow:auto;max-width:100%;padding:12px;background:#102126;border-radius:8px"></pre><p class="meta">Build '+build+'</p></section>';
    const box = document.getElementById('startup-detail');
    if (box) box.textContent = detail;
    // Keep immediate diagnostics even if module loading itself is broken.
    import('./web_i18n.js').then(({tr,applySiteLanguage})=>{
      applySiteLanguage(app);if(box&&!errors.length)box.textContent=tr('diagnostics.detail');
    }).catch(()=>{});
  }, 2500);
})();
