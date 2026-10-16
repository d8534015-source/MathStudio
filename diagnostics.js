(() => {
  const build = 'v40-full-meeting-auto-refresh';
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
    app.innerHTML = '<section class="panel auth"><p class="eyebrow">Startup diagnostic</p><h1>Math Studio could not open</h1><p>The server page loaded, but the app JavaScript did not start.</p><pre id="startup-detail" style="white-space:pre-wrap;overflow:auto;max-width:100%;padding:12px;background:#102126;border-radius:8px"></pre><p class="meta">Build '+build+'</p></section>';
    const box = document.getElementById('startup-detail');
    if (box) box.textContent = detail;
  }, 2500);
})();
