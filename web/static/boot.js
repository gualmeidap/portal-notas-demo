/* Start-up: language toggle, boot screen (browser runtime), first page. */
(async () => {
  renderShell();
  $('#boot-note').textContent = tb('boot_note');
  if (Runtime.MODE === 'browser') {
    const boot = $('#boot');
    boot.hidden = false;
    try {
      await Runtime.boot((key, pct) => {
        if (key) $('#boot-step').textContent = tb(key);
        $('#boot-fill').style.width = `${pct}%`;
      });
    } catch (e) {
      $('#boot-step').textContent = tb('boot_failed') + e.message;
      return;
    }
    boot.hidden = true;
  }
  try {
    const cfg0 = await api('GET', 'api/settings');
    mailbox = cfg0.settings.mailbox;
    const s = await api('GET', 'api/summary');
    monitorOn = !!s.monitor;
  } catch (_) { /* settings are cosmetic here */ }
  if (!location.hash) location.hash = '#/overview';
  route();
})();
