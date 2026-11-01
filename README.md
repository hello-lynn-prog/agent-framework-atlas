# Agent 框架底层对比图谱

> 用源码级审计回答：主流 Agent SDK / 框架，各自把 agent loop、工具系统、状态管理、扩展点放在了哪一行、怎么二次开发。

覆盖 8 个项目，分两层：

- **六方对比矩阵**（2026-10-06，55 个架构概念 × 6 项目 + 9 概念深比）：codex · claude-agent-sdk-python · pi-mono · openai-agents-python · hermes-agent · langgraphjs
- **单独深审**：deepagents（2026-10-08 补审，含三张自绘机制图）、DeepSeek Harness（2026-10-01 旧审计，未随六方刷新）

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `agent-code-atlas-output/<框架>/audit.json + report.html` | 8 份单项目审计（统一数据模型 + 交互式图谱） |
| `agent-code-atlas-output/comparison-report.html` | 六方横向对比报告 |
| `agent-code-atlas-output/deepagents/学习路线图.html` | deepagents 五关学习路线（L1 会查 / L2 会讲 / L3 会改） |
| `agent-code-atlas-output/deepagents/钩子架构图.html` | deepagents 五检查站 × 中间件挂靠图 |
| `agent-code-atlas-output/deepagents/langgraph-loop图.html` | langgraph 引擎循环（Pregel 超步）图解 |
| `agent-code-atlas-output/codex/codex-项目树.md` | codex 154 crate 分层标注树（约 157 万行） |
| `visuals/` | 图解速览：八家 SDK 速览·可点击版、codex-flow、dsh 对比图等 |
| `.atlas-work/comparison/` | 比较矩阵组装脚本 |
| `推文-八家Agent框架源码审计.md` | 面向公众的八家总结长文 |

## 怎么看

1. 快速看六方结论 → 双击 `agent-code-atlas-output/comparison-report.html`
2. 深挖某个框架 → 双击对应目录下的 `report.html`
3. 学 deepagents → 该目录下三张图（路线图 → 钩子架构 → 引擎循环）
4. 一页速览八家 → `visuals/sdk-八家速览-可点击版.html`（格子可点、hash 深链接）

全部 HTML 为自包含单文件，下载后离线（file://）打开即用。

## 被审计项目与基线

| 审计对象 | 官方仓库 | 审计基线 |
| --- | --- | --- |
| codex | https://github.com/openai/codex | 源码快照（无 .git，行号以快照为准） |
| claude-agent-sdk-python | https://github.com/anthropics/claude-agent-sdk-python | 源码快照（同上） |
| pi-mono | https://github.com/badlogic/pi-mono | `6f755151`（2026-10-06） |
| openai-agents-python | https://github.com/openai/openai-agents-python | `08e5c43`（2026-10-06） |
| hermes-agent | https://github.com/NousResearch/hermes-agent | 源码快照（同上） |
| langgraphjs | https://github.com/langchain-ai/langgraphjs | `2478e098`（2026-10-06） |
| deepagents | https://github.com/langchain-ai/deepagents | `6a3a12b`（2026-10-08） |
| deepseek-harness | https://github.com/deepseek-ai/deepseek-harness | 2026-10-01 审计，未随六方刷新 |

## 审计工具

所有审计由自研 skill **agent-code-atlas** 生成：统一架构本体 + 证据分级（runtime > test > code > config > docs > inference）+ 四态实现状态（implemented / delegated / absent / unknown）。

工具仓库：https://github.com/hello-lynn-prog/agent-code-atlas

## 声明

- 本仓库只包含分析产物，不含被审计项目的源码；各项目版权归原仓库所有，入口见上表。
- Claude Code CLI 本身为闭源产品、未纳入审计；本仓库中 claude 相关审计对象是其开源的 Python SDK。
- 审计为静态分析结论，每条结论的置信度与证据等级标注在对应 `audit.json` 中；标 `unknown` 的不猜测。
