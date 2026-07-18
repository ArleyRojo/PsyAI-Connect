import re

from django.middleware.csrf import get_token


class CSRFMetaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return response

        try:
            html = response.content.decode("utf-8", errors="ignore")
        except Exception:
            return response

        if 'name="csrf-token"' in html:
            return response

        try:
            token = get_token(request)
        except Exception:
            token = ""

        script = f"""<meta name="csrf-token" content="{token}">
<script>
(function(){{
  var tokenMeta = document.querySelector('meta[name="csrf-token"]');
  if (!tokenMeta || window.__csrfInstalled) return;
  window.__csrfInstalled = true;
  var origFetch = window.fetch;
  window.fetch = function(url, opts) {{
    opts = opts || {{}};
    opts.headers = opts.headers || {{}};
    if (opts.method && opts.method.toUpperCase() !== 'GET') {{
      if (tokenMeta) opts.headers['X-CSRFToken'] = tokenMeta.getAttribute('content');
    }}
    return origFetch.call(this, url, opts);
  }};
}})();
</script>
"""
        updated = re.sub(
            r"<head[^>]*>",
            lambda m: m.group(0) + "\n" + script.strip(),
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        if updated == html:
            updated = re.sub(
                r"<html[^>]*>",
                lambda m: m.group(0) + "\n" + script.strip(),
                html,
                count=1,
                flags=re.IGNORECASE,
            )
        if updated == html:
            updated = script.strip() + "\n" + html

        response.content = updated.encode("utf-8")
        response["Content-Length"] = str(len(response.content))
        return response
