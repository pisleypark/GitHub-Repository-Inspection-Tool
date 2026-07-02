# AI Coding Prompts

本文件记录开发过程中使用的关键 Prompt，便于提交材料说明 AI Coding 工具的使用方式。

## Prompt 1：后端第一版

> 我要做一个 GitHub 仓库体检工具。请先完成后端第一版，使用 FastAPI。用户传入一个公开 GitHub 仓库 URL，后端能解析 owner/repo，并通过 GitHub API 获取仓库信息。实现 `/analyze`，返回 stars、forks、description、default_branch、updated_at、language distribution、README 内容和最多 300 个文件路径。

## Prompt 2：接入通义千问和三个 Agent

> 现在请接入通义千问，并实现三个 Agent：代码审计 Agent、产品价值 Agent、总分裁判 Agent。模型只能基于 repo_context 分析，不要编造没有提供的信息。如果模型返回的不是合法 JSON，要做一次简单修复或返回清晰错误。

## Prompt 3：添加 React + Vite 前端

> 现在请添加一个简单前端，用 React + Vite。用户在网页输入 GitHub 仓库 URL，点击按钮后调用后端 POST `/analyze`，展示仓库名称、stars、forks、主要语言、Agent A/B/C 的分析结果和最终评分建议。

## Prompt 4：添加 SSE 流式分析

> 现在请添加 SSE 流式分析接口。新增 GET `/analyze/stream`，返回 parsing_url、fetching_github、code_audit、product_analysis、final_judge、done、error 等阶段消息。前端优先使用 EventSource 调用流式接口，页面展示阶段进度列表，最后展示完整报告。

## Prompt 5：补齐提交材料

> 补充 README.md，包含项目介绍、技术栈、本地运行步骤、环境变量说明、后端接口说明、示例 GitHub URL、多 Agent 设计说明。新增 docs/prompts.md，记录使用 AI Coding 工具的 3-5 条关键 Prompt。
