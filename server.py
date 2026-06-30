"""
Pure Chat — 零注入多 API 代理服务器
======================================
不注入任何 system prompt、不添加任何工具、
不修改任何消息内容。原样转发你的话给 LLM，
原样返回 LLM 的话给你。

支持: OpenAI / DeepSeek / Anthropic / Groq / xAI / 自定义

使用: python server.py → 浏览器打开 http://localhost:3721
"""

import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 3721
ROOT = Path(__file__).parent

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "auth": "bearer",
        "format": "openai",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "auth": "bearer",
        "format": "openai",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-opus-4-8",
        "auth": "x-api-key",
        "format": "anthropic",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b",
        "auth": "bearer",
        "format": "openai",
    },
    "xai": {
        "name": "xAI",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3",
        "auth": "bearer",
        "format": "openai",
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "default_model": "",
        "auth": "bearer",
        "format": "openai",
    },
}


class Handler(SimpleHTTPRequestHandler):
    """静态文件 + API 代理"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ── 路由 ───────────────────────────────────────────
    def do_GET(self):
        if self.path == "/api/providers":
            self._json(200, PROVIDERS)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            self._proxy_chat()
        else:
            self.send_error(404)

    # ── 核心代理逻辑 ────────────────────────────────────
    def _proxy_chat(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length))

        provider_id = body.get("provider", "deepseek")
        provider = PROVIDERS.get(provider_id, PROVIDERS["deepseek"])
        base_url = body.get("base_url") or provider["base_url"]
        model = body.get("model") or provider["default_model"]
        messages = body.get("messages", [])
        api_key = self.headers.get("x-api-key", "").strip()

        if not api_key:
            self._json(401, {"error": "请在底部设置 API Key"})
            return

        fmt = provider["format"]

        if fmt == "anthropic":
            req = self._build_anthropic(base_url, model, messages, api_key)
        else:
            req = self._build_openai(base_url, model, messages, api_key)

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                if fmt == "anthropic":
                    reply = self._parse_anthropic(data)
                else:
                    reply = data["choices"][0]["message"]["content"]
                self._json(200, {"reply": reply})
        except urllib.error.HTTPError as e:
            body_bytes = e.read()
            try:
                err = json.loads(body_bytes.decode("utf-8", errors="replace"))
                msg = err.get("error", {}).get("message", str(e))
            except Exception:
                msg = body_bytes.decode("utf-8", errors="replace")[:500]
            self._json(e.code, {"error": msg})
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ── 请求构建 ───────────────────────────────────────
    def _build_openai(self, base_url, model, messages, api_key):
        payload = {"model": model, "messages": messages, "stream": False}
        url = base_url.rstrip("/") + "/chat/completions"
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

    def _build_anthropic(self, base_url, model, messages, api_key):
        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        url = base_url.rstrip("/") + "/v1/messages"
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )

    def _parse_anthropic(self, data):
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""

    # ── 工具方法 ───────────────────────────────────────
    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            print(f"→ {args[0]}")


if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║          Pure Chat  v2.0                ║
║   零注入 · 无提示词 · 多 API 纯对话       ║
╠══════════════════════════════════════════╣
║  OpenAI / DeepSeek / Anthropic / Groq   ║
║  xAI / 自定义兼容 API                    ║
╠══════════════════════════════════════════╣
║  打开 → http://localhost:{PORT}           ║
║  按 Ctrl+C 停止                          ║
╚══════════════════════════════════════════╝
""")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
        server.shutdown()
