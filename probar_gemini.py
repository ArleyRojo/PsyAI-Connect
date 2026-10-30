import time, requests

# Lee la clave del .env sin instalar nada extra
KEY = ""
for line in open(".env", encoding="utf-8"):
    if line.startswith("GEMINI_API_KEY="):
        KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
if not KEY:
    raise SystemExit("No encontré GEMINI_API_KEY en .env")

URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
msg = {"contents": [{"role": "user", "parts": [{"text": "me siento solo"}]}]}

def probe(name, model, body):
    t = time.time()
    try:
        r = requests.post(URL.format(model), json=body,
                          headers={"x-goog-api-key": KEY}, timeout=(5, 25))
        print(f"{name}: HTTP {r.status_code} en {time.time()-t:.1f}s")
    except Exception as e:
        print(f"{name}: FALLÓ a los {time.time()-t:.1f}s -> {type(e).__name__}")

M = "gemini-3.5-flash-lite"
probe("1 mínimo", M, msg)
probe("2 temp 0.55", M, {**msg, "generationConfig": {"temperature": 0.55}})
probe("3 thinking minimal", M, {**msg, "generationConfig": {"thinkingConfig": {"thinkingLevel": "minimal"}}})
probe("4 otro modelo", "gemini-2.5-flash-lite", msg)