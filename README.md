# Pure Chat

纯净的 LLM API 对话界面。**零 system prompt 注入、零工具调用、零内容修改**——你发什么，API 就收什么；API 回什么，你就看到什么。

## 支持的 API（14 个）

| 提供商 | 默认模型 | API 格式 |
|---|---|---|
| OpenAI | gpt-4o | OpenAI |
| DeepSeek | deepseek-chat | OpenAI |
| Anthropic | claude-opus-4-8 | Anthropic 原生 |
| Google Gemini | gemini-2.5-flash | Gemini 原生 |
| Groq | llama-3.3-70b | OpenAI |
| xAI | grok-3 | OpenAI |
| Together AI | Llama-3.3-70B | OpenAI |
| Fireworks AI | llama-v3p3-70b | OpenAI |
| Mistral | mistral-large-latest | OpenAI |
| Perplexity | sonar-pro | OpenAI |
| OpenRouter | openai/gpt-4o | OpenAI |
| Ollama (本地) | llama3 | OpenAI (无需 Key) |
| 自定义 | — | OpenAI 兼容 |

## 快速开始

```bash
git clone https://github.com/isheng-eqi/pure-chat.git
cd pure-chat
python server.py
# 浏览器打开 http://localhost:3721
```

**零依赖**：Python 3 标准库即可。无需 pip install。

## 架构

```
浏览器 → Python 代理 (localhost:3721) → LLM API
                                          ├── OpenAI 兼容 → /chat/completions
                                          ├── Anthropic    → /v1/messages
                                          └── Gemini       → /models/{model}:generateContent
```

- API Key 存浏览器 localStorage，后端不落盘
- 对话历史在浏览器端，刷新即清空
- 所有设置本地保存，下次打开自动恢复

## License

MIT
