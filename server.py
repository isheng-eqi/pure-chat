"""
Pure Chat — 零注入多 API 代理服务器
======================================
不注入任何 system prompt、不添加任何工具、
不修改任何消息内容。

支持 14 个主流 LLM API，3 种后端格式。

使用: python server.py → 浏览器打开 http://localhost:3721
"""

import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 3721
ROOT = Path(__file__).parent

# ── 提供商注册表 ─────────────────────────────────────
# auth 类型: bearer | x-api-key | query | none
# format 类型: openai | anthropic | google

PROVIDERS = {
    # ── OpenAI 兼容（Bearer Token）─────────────────
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
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "auth": "bearer",
        "format": "openai",
    },
    "fireworks": {
        "name": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "auth": "bearer",
        "format": "openai",
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "auth": "bearer",
        "format": "openai",
    },
    "perplexity": {
        "name": "Perplexity",
        "base_url": "https://api.perplexity.ai",
        "default_model": "sonar-pro",
        "auth": "bearer",
        "format": "openai",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o",
        "auth": "bearer",
        "format": "openai",
    },
    # ── Anthropic 原生格式 ──────────────────────────
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-opus-4-8",
        "auth": "x-api-key",
        "format": "anthropic",
    },
    # ── Google Gemini 原生格式 ──────────────────────
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.5-flash",
        "auth": "query",
        "format": "google",
    },
    # ── 本地 / 无鉴权 ───────────────────────────────
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "auth": "none",
        "format": "openai",
    },
    # ── 自定义 ──────────────────────────────────────
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

    # ── 核心代理 ──────────────────────────────────────
    def _proxy_chat(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length))

        provider_id = body.get("provider", "")
        provider = PROVIDERS.get(provider_id)
        if not provider:
            self._json(400, {"error": "请选择一个 API 提供商"})
            return

        base_url = body.get("base_url") or provider["base_url"]
        model = body.get("model") or provider["default_model"]
        messages = body.get("messages", [])
        api_key = self.headers.get("x-api-key", "").strip()
        fmt = provider["format"]

        # 鉴权检查（none 类型无需 Key）
        if provider["auth"] != "none" and not api_key:
            self._json(401, {"error": "请设置 API Key"})
            return

        # 构建请求
        if fmt == "anthropic":
            req = self._build_anthropic(base_url, model, messages, api_key)
        elif fmt == "google":
            req = self._build_google(base_url, model, messages, api_key)
        else:
            req = self._build_openai(base_url, model, messages, api_key)

        # 发送 & 解析
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
                if fmt == "anthropic":
                    reply = self._parse_anthropic(data)
                elif fmt == "google":
                    reply = self._parse_google(data)
                else:
                    reply = data["choices"][0]["message"]["content"]
                self._json(200, {"reply": reply})
        except urllib.error.HTTPError as e:
            self._handle_error(e)
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ── OpenAI 兼容格式 ───────────────────────────────
    def _build_openai(self, base_url, model, messages, api_key):
        payload = {"model": model, "messages": messages, "stream": False}
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )

    # ── Anthropic 原生格式 ─────────────────────────────
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

    # ── Google Gemini 原生格式 ─────────────────────────
    def _build_google(self, base_url, model, messages, api_key):
        # 转换 OpenAI 格式 → Gemini 格式
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {"contents": contents}
        url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}"
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    def _parse_google(self, data):
        candidates = data.get("candidates", [])
        if not candidates:
            # 检查是否有 safety 拦截
            if "promptFeedback" in data:
                return f"[被安全策略拦截: {json.dumps(data['promptFeedback'], ensure_ascii=False)}]"
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)

    # ── 错误处理 ──────────────────────────────────────
    def _handle_error(self, e):
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            self._json(e.code, {"error": f"HTTP {e.code}"})
            return

        # Anthropic 错误格式
        if "error" in body and isinstance(body["error"], dict):
            self._json(e.code, {"error": body["error"].get("message", str(body))})
        # Google 错误格式
        elif "error" in body:
            err = body["error"]
            self._json(e.code, {"error": f"{err.get('code', e.code)}: {err.get('message', str(err))}"})
        # OpenAI 兼容错误格式
        elif "error" in body and isinstance(body["error"], dict):
            self._json(e.code, {"error": body["error"].get("message", str(body))})
        else:
            self._json(e.code, {"error": str(body)[:500]})

    # ── 工具方法 ───────────────────────────────────────
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

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
    names = ", ".join(p["name"] for p in PROVIDERS.values())
    print(f"""
╔══════════════════════════════════════════╗
║          Pure Chat  v3.0                ║
║   零注入 · 14 提供商 · 3 种 API 格式      ║
╠══════════════════════════════════════════╣
║  {names}
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
