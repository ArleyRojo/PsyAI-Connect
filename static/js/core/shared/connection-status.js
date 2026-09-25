(function () {
  var indicator = null;
  var reconnectTimer = null;
  var isOnline = navigator.onLine;

  function createIndicator() {
    if (indicator) return;
    indicator = document.createElement('div');
    indicator.id = 'connection-status-indicator';
    indicator.style.cssText = 'position:fixed;bottom:16px;right:16px;padding:8px 12px;border-radius:6px;font-size:12px;z-index:9999;display:flex;align-items:center;gap:6px;box-shadow:0 2px 8px rgba(0,0,0,.15);transition:opacity .3s';
    indicator.innerHTML = '<span class="dot"></span><span class="text"></span>';
    document.body.appendChild(indicator);
    updateUI();
  }

  function updateUI() {
    if (!indicator) return;
    var dot = indicator.querySelector('.dot');
    var text = indicator.querySelector('.text');
    if (isOnline) {
      indicator.style.background = '#d4edda';
      indicator.style.color = '#155724';
      indicator.style.border = '1px solid #c3e6cb';
      dot.style.cssText = 'width:8px;height:8px;border-radius:50%;background:#28a745';
      text.textContent = 'En línea';
    } else {
      indicator.style.background = '#f8d7da';
      indicator.style.color = '#721c24';
      indicator.style.border = '1px solid #f5c6cb';
      dot.style.cssText = 'width:8px;height:8px;border-radius:50%;background:#dc3545;animation:blink 1s infinite';
      text.textContent = 'Sin conexión';
      if (!document.getElementById('conn-blink-style')) {
        var style = document.createElement('style');
        style.id = 'conn-blink-style';
        style.textContent = '@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}';
        document.head.appendChild(style);
      }
    }
  }

  function onOnline() {
    isOnline = true;
    updateUI();
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(function () {
      if (indicator) {
        indicator.style.opacity = '0';
        setTimeout(function () { indicator && indicator.remove(); indicator = null; }, 300);
      }
    }, 3000);
  }

  function onOffline() {
    isOnline = false;
    createIndicator();
    updateUI();
    clearTimeout(reconnectTimer);
  }

  window.addEventListener('online', onOnline);
  window.addEventListener('offline', onOffline);

  if (!isOnline) {
    createIndicator();
    updateUI();
  }
})();