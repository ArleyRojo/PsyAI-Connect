(function () {
  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    return getCookie('csrftoken');
  }

  window.CSRF = {
    getToken: getCsrfToken,
    getHeaderName: function () { return 'X-CSRFToken'; }
  };

  if (typeof fetch !== 'undefined') {
    var originalFetch = window.fetch;
    window.fetch = function (url, options) {
      options = options || {};
      var method = (options.method || 'GET').toUpperCase();
      if (['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1) {
        var token = getCsrfToken();
        if (token) {
          options.headers = options.headers || {};
          if (!(options.headers instanceof Headers)) {
            options.headers = new Headers(options.headers);
          }
          options.headers.set('X-CSRFToken', token);
        }
      }
      options.credentials = options.credentials || 'include';
      return originalFetch.call(this, url, options);
    };
  }
})();