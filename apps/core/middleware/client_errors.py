import re


def _client_error_reporter_script():
    return """
<script>
(function () {
  if (window.__psyaiErrorReporterInstalled) return;
  window.__psyaiErrorReporterInstalled = true;

  function describeReason(reason) {
    if (!reason) return "";
    if (reason.stack) return reason.stack;
    if (reason.message) return reason.message;
    try { return JSON.stringify(reason); } catch (_) { return String(reason); }
  }

  function sendClientError(type, message, details) {
    try {
      var csrfMeta = document.querySelector('meta[name="csrf-token"]');
      var csrfHeaders = { "Content-Type": "application/json" };
      if (csrfMeta) csrfHeaders['X-CSRFToken'] = csrfMeta.getAttribute('content');
      fetch("/api/client-errors", {
        method: "POST",
        headers: csrfHeaders,
        keepalive: true,
        body: JSON.stringify({
          type: type,
          message: message || "",
          details: details || "",
          page: window.location.pathname + window.location.search
        })
      }).catch(function () {});
    } catch (_) {}
  }

  window.addEventListener("error", function (event) {
    sendClientError("javascript", event.message, [
      event.filename || "",
      event.lineno || "",
      event.colno || "",
      event.error && event.error.stack ? event.error.stack : ""
    ].filter(Boolean).join(" | "));
  });

  window.addEventListener("unhandledrejection", function (event) {
    sendClientError("promise", describeReason(event.reason), "");
  });
})();
</script>
""".strip()


class ClientErrorReporterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        if not hasattr(response, "get"):
            return response
        content_type = response.get("Content-Type", "")
        if response.status_code >= 400 or "text/html" not in content_type:
            return response

        try:
            html = response.content.decode("utf-8", errors="ignore")
        except Exception:
            return response

        if "__psyaiErrorReporterInstalled" in html or "</body>" not in html.lower():
            return response

        script = _client_error_reporter_script()
        updated = re.sub(r"</body>", script + "\n</body>", html, count=1, flags=re.IGNORECASE)
        response.content = updated.encode("utf-8")
        response["Content-Length"] = str(len(response.content))
        return response
