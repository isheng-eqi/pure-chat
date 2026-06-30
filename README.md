# Pure Chat

纯净的 LLM API 对话界面。**零 system prompt 注入、零工具调用、零内容修改**——你发什么，API 就收什么；API 回什么，你就看到什么。

## 支持的 API

| 提供商 | 默认模型 |
|---|---|
| OpenAI | gpt-4o |
| DeepSeek | deepseek-chat |
| Anthropic | claude-opus-4-8 |
| Groq | llama-3.3-70b |
| xAI | grok-3 |
| 自定义 | 任意 OpenAI 兼容 API |

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/isheng-eqi/pure-chat.git
cd pure-chat

# 2. 启动（Python 3 标准库，无需 pip install）
python server.py

# 3. 浏览器打开 http://localhost:3721
# 4. 选择提供商 → 填入 API Key → 开始对话
```

## 为什么做这个

所有 LLM 网页版（chat.openai.com、chat.deepseek.com、claude.ai）都内置了大量系统提示词和行为规范。这个项目通过 API 直连，**不注入任何额外内容**，是你不本地部署的情况下最接近「裸」模型的方式。

## 架构

```
浏览器 (index.html)
    │  fetch('/api/chat', { provider, model, messages, x-api-key })
    ▼
本地代理 (server.py :3721)
    │  根据 provider 选择 API 格式：
    │  - OpenAI 兼容 → POST {base}/chat/completions
    │  - Anthropic    → POST {base}/v1/messages
    │  只传 model + messages，不传 system/tools/temperature
    ▼
LLM API → 纯文本回复 → 浏览器显示
```

- **零依赖**：后端只用 Python 标准库（`http.server` + `urllib`）
- **API Key 存浏览器 localStorage**，后端不落盘
- **对话历史在浏览器端**，刷新即清空
- **所有设置本地保存**，下次打开自动恢复

## 自定义 API

选择「自定义」提供商后，可以填入任意 OpenAI 兼容的 API 地址，例如：

```
Ollama 本地:    http://localhost:11434/v1
vLLM 本地:      http://localhost:8000/v1
其他代理:       https://your-proxy.com/v1
```

模型名手动输入，格式取决于你的后端服务。

## 与网页版的区别

| | 网页版 | Pure Chat |
|---|---|---|
| system prompt | 官方注入 | **无** |
| 工具调用 | 搜索、文件上传等 | **无** |
| 采样参数 | 官方默认 | **API 默认** |
| 账号 | 需注册 | **只需 API Key** |
| 内容过滤 | ✅ | ✅（API 层不可绕过） |

## 仍然存在的限制

即使去掉了所有能去掉的注入，以下因素仍不可消除：

- **RLHF 对齐** —— 模型训练时就刻入了安全对齐行为
- **API 层安全过滤** —— 各厂商服务端的内容审核
- **API 计费与限速** —— 商业模式决定的

要完全解除这些限制，只能本地部署开源模型。

## License

MIT
