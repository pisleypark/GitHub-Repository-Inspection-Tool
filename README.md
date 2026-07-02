# GitHub 仓库体检工具

## 项目介绍

一个面向公开 GitHub 仓库的体检工具。用户输入仓库 URL 后，后端会获取 GitHub 仓库上下文，并调用三个通义千问 Agent 分析代码工程质量、产品价值和最终体检结论；前端通过 SSE 实时展示分析阶段进度，完成后展示完整报告。

## 技术栈

- 后端：FastAPI、httpx、python-dotenv
- 数据来源：GitHub REST API
- 模型接口：通义千问 DashScope OpenAI 兼容接口，默认模型 `qwen-plus`
- 前端：React、Vite、TypeScript
- 实时进度：Server-Sent Events
- 测试：pytest、Vitest、Testing Library

## 本地运行

### 1. 启动后端

```powershell
cd F:\writen_question\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `backend/.env` 中填写环境变量后启动：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 启动前端

```powershell
cd F:\writen_question\frontend
npm install
npm run dev -- --host 127.0.0.1
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

## 环境变量

后端 `backend/.env`：

```env
GITHUB_TOKEN=
DASHSCOPE_API_KEY=你的 DashScope API Key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

- `GITHUB_TOKEN`：可选。为空时仍可访问公开仓库，但 GitHub 匿名 API rate limit 更低。
- `DASHSCOPE_API_KEY`：必填。用于调用通义千问 OpenAI 兼容接口。
- `DASHSCOPE_BASE_URL`：可选。默认使用阿里云百炼兼容接口地址。

前端可选 `.env`：

```env
VITE_API_BASE_URL=http://localhost:8000
```

未配置时，前端默认请求 `http://localhost:8000`。

## 后端接口

### POST /analyze

普通非流式分析接口，适合调试。

请求：

```json
{
  "repo_url": "https://github.com/langchain-ai/langgraph"
}
```

响应：

```json
{
  "repo_context": {},
  "agents": {
    "code_auditor": {},
    "product_analyst": {},
    "final_judge": {}
  }
}
```

### GET /analyze/stream

SSE 流式分析接口，前端默认优先使用。

示例：

```powershell
curl.exe -N "http://127.0.0.1:8000/analyze/stream?repo_url=https%3A%2F%2Fgithub.com%2Flangchain-ai%2Flanggraph"
```

每条 SSE 消息的 JSON 格式：

```json
{
  "stage": "code_audit",
  "message": "Agent A 正在分析代码结构",
  "data": null
}
```

阶段包括：

- `parsing_url`：正在解析 GitHub URL
- `fetching_github`：正在获取 GitHub 仓库信息
- `code_audit`：Agent A 正在分析代码结构
- `product_analysis`：Agent B 正在分析 README 和产品价值
- `final_judge`：Agent C 正在生成最终评分
- `done`：完成，`data` 包含完整报告
- `error`：失败，`message` 包含错误原因

## 示例 GitHub URL

```text
https://github.com/langchain-ai/langgraph
```

## 多 Agent 设计

### Agent A：代码审计 Agent

输入 `repo_context`，根据目录结构、语言分布、配置文件、tests、CI、src 目录判断代码工程质量。输出代码质量评分、优势、风险和建议。

### Agent B：产品价值 Agent

输入 `repo_context`，根据 README、stars、forks、更新时间和项目描述判断 README 清晰度、实用价值和开源活跃度。输出产品价值评分、README 清晰度、活跃度、优势、风险和建议。

### Agent C：总分裁判 Agent

输入 `repo_context`、Agent A 结果和 Agent B 结果，生成最终体检报告。输出最终评分、等级、摘要、维度分数、主要问题和优先建议。

所有 Agent 的 prompt 都要求模型只能基于 `repo_context` 和已提供的 Agent 结果分析，不允许编造未提供的信息，并要求只返回合法 JSON。

## 测试

后端：

```powershell
cd F:\writen_question\backend
python -B -m pytest tests -q
```

前端：

```powershell
cd F:\writen_question\frontend
npm test
npm run build
```
