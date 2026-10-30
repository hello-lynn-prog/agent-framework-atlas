# Codex 项目树（依据源码实测标注）

> 数据来源：`03-sdk-research/harness-research/codex`，2026-10-09 逐 crate 统计 `.rs` 行数。
> 全 workspace：**154 个 Rust crate（顶层 111 + ext/ 16 + utils/ 27），约 157 万行 Rust**。
> 行数单位 k = 千行，均为 `src/` 下 `.rs` 文件实测。

```
codex/  （openai/codex monorepo，Apache-2.0）
│
├── codex-rs/                    ★ 主战场：cargo workspace，154 个 crate，~157 万行
│   │                             （另有 vendor/ 第三方代码、docs/ crate 内文档）
│   │
│   ├── ① 入口层（壳）—— 四种打开方式，共用同一个引擎
│   │   ├── tui/                 430k 行  交互式终端 UI（全仓最大 crate，比引擎还大）
│   │   │                                 chatwidget=会话主窗 / bottom_pane=输入区 / app_backtrack=回溯
│   │   ├── cli/                  30k 行  `codex` 命令入口：main.rs 分发子命令
│   │   │                                 （login / mcp / plugin / doctor / debug_sandbox / daemon…）
│   │   ├── exec/                 6k 行   `codex exec` 非交互一次性执行（脚本 / CI 用）
│   │   ├── app-server/          62k 行   JSON-RPC 服务端：给 IDE 插件、桌面 App 当后端
│   │   └── arg0/                <1k 行   按可执行文件名换皮分派（一个二进制多个身份）
│   │
│   ├── ② 引擎层 —— agent loop 所在地
│   │   ├── core/               245k 行   ★ 引擎本体。主循环 = core/src/session/turn.rs 的 run_turn
│   │   │                                 client.rs=模型流式调用；compact*.rs=上下文压缩
│   │   │                                 agent/=子代理；hook_runtime.rs=钩子；skills.rs=技能
│   │   │                                 exec*.rs=shell 执行；guardian/=审查；tasks/ thread_manager/ session/=调度
│   │   ├── core-api/            <1k 行   core 对外的薄 API 封装
│   │   └── core-plugins/        48k 行   内置插件集（plugin/=插件接口与注册；core-plugin-common/ 公共件）
│   │
│   ├── ③ 协议层 —— 壳与引擎之间的"合同"
│   │   └── protocol/            32k 行   Op 命令 / EventMsg 事件 / 审批四态
│   │                                     （AskForApproval、ReviewDecision）/ 模型元数据 / 权限画像
│   │
│   ├── ④ 工具层 —— 模型的手牌怎么打出去
│   │   ├── tools/                8k 行   ToolExecutor trait、ToolSpec、JSON Schema 校验、工具目录
│   │   ├── apply-patch/          5k 行   自研 V4A 补丁协议（模型改文件走这里）
│   │   ├── shell-command/       10k 行   shell 命令构造与解析
│   │   ├── shell-escalation/     2k 行   沙箱内→沙箱外的提权请求
│   │   └── code-mode 家族       27k 行   code-mode / -host / -protocol / -runtime（+ v8-poc）
│   │                                     在 V8 引擎里写 JS 一次调一串工具
│   │
│   ├── ⑤ 模型接入层 —— 只做客户端，仓库里没有模型
│   │   ├── model-provider/       8k 行   provider 抽象（接第三方 Responses 端点的关键位）
│   │   ├── model-provider-info/  2k 行   provider 配置结构
│   │   ├── codex-api/           15k 行   OpenAI 后端 API 客户端
│   │   ├── codex-backend-openapi-models/ 1k 行  OpenAPI 生成的模型定义
│   │   ├── models-manager/       4k 行   模型列表与能力元数据
│   │   ├── responses-api-proxy/  1k 行   Responses API 代理
│   │   ├── ollama/ lmstudio/    ~2k 行   本地模型接入
│   │   └── http-client/ websocket-client/ websocket-auth/  14k 行  传输层
│   │
│   ├── ⑥ 沙箱与安全层 —— 执行器的"材质"
│   │   ├── sandboxing/          11k 行   统一编排：按平台选沙箱
│   │   ├── execpolicy/           2k 行   Starlark 静态命令规则引擎（allow / prompt / forbidden）
│   │   ├── linux-sandbox/        9k 行   Landlock + seccomp 实现
│   │   ├── windows-sandbox-rs/  29k 行   Windows 受限令牌实现（+ windows-sandbox-service/ 6k）
│   │   ├── mxc-sandbox/ bwrap/  ~2k 行   其它沙箱后端
│   │   ├── network-proxy/       30k 行   沙箱内网络管控代理
│   │   └── guardian-context/    7k 行    守护审查上下文（+ user-verification/ process-hardening/ ~1.5k）
│   │
│   ├── ⑦ 扩展点层 —— 插座们
│   │   ├── rmcp-client/         28k 行   MCP 客户端（stdio / streamable-HTTP）
│   │   ├── codex-mcp/           25k 行   MCP 集成层：工具目录、绑定、协议模式
│   │   ├── hooks/               16k 行   钩子引擎（engine + declarations + config_rules）
│   │   ├── skills/ prompts/      5k 行   技能加载、提示词模板
│   │   ├── connectors/          ~5k 行   外部连接器（+ stdio-to-uds/ 桥接）
│   │   └── plugin/               1k 行   插件机制接口
│   │
│   ├── ⑧ 持久化层 —— 会话记录与状态（checkpoint 的对应物）
│   │   ├── rollout/             17k 行   JSONL 会话记录：resume / fork 的数据源
│   │   ├── rollout-trace/       13k 行   rollout 追踪视图
│   │   ├── thread-store/        35k 行   存储中立的 thread 持久化接口（只认 ThreadId）
│   │   ├── state/               26k 行   SQLite：rollout 元数据镜像
│   │   ├── history/ message-history/ attachment-store/  ~6k 行
│   │   └── codex-home/          <1k 行   ~/.codex 目录布局
│   │
│   ├── ⑨ IDE 集成协议栈 —— app-server / exec-server 家族
│   │   ├── app-server-protocol/ 36k 行   JSON-RPC 协议定义
│   │   ├── app-server-transport/ 18k 行  传输层
│   │   ├── app-server-client/ daemon/ test-client/  17k 行
│   │   └── exec-server/ + protocol/  49k 行  独立执行服务进程（与 UI 进程分离）
│   │
│   ├── ⑩ 周边服务
│   │   ├── login/               19k 行   ChatGPT / API key 登录
│   │   ├── keyring-store/ secrets/ aws-auth/ workload-identity/  ~4k 行  凭证
│   │   ├── cloud-tasks 家族 + chatgpt/ cloud-config/  ~11k 行  云端任务
│   │   ├── realtime-webrtc/ voice-host/  ~7k 行  语音
│   │   ├── analytics/ otel/ feedback/  ~27k 行  遥测与反馈（+ otel-trace-websocket/）
│   │   ├── git-utils/ worktree/ file-search/ file-watcher/ file-system/  ~10k 行
│   │   ├── memories/ agent-identity/ agent-roles/ agent-graph-store/
│   │   │   agent-message-board-client/  ~4k 行  记忆与多代理
│   │   ├── external-agent-migration/ 16k 行  从其它 agent 工具迁移
│   │   ├── config/              30k 行   分层配置体系（+ config-schema/；features/ 3.5k 功能开关）
│   │   └── install-context/ diagnostics/ response-debug-context/ build-info/
│   │       tcp-tunnel/ uds/     ~4k 行   杂项
│   │
│   ├── ext/                     16 个扩展 crate，约 54k 行
│   │   ├── skills/              19k 行   技能扩展（ext 里最大）
│   │   ├── guardian-v2/         13k 行   守护审查 v2（+ guardian-reviewer/ 3k、goal/ 3k）
│   │   ├── mcp/ agent-message-board/ memories/ extension-api/  ~11k 行
│   │   └── image-generation/ web-search/ history-notes/ queue/
│   │       git-attribution/ items/ agent/ connectors/  ~5k 行
│   │
│   └── utils/                   27 个基础工具 crate，约 24k 行
│       ├── pty/                 10k 行   伪终端（utils 里最大）
│       ├── path-uri/ stream-parser/ image/ absolute-path/  ~8k 行
│       └── 其余 22 个           ~6k 行   string / template / cache / fuzzy-match / home-dir…
│
├── sdk/                         官方 SDK（把 codex 当库嵌进你的程序）
│   ├── typescript/              24 个 ts：codex.ts / thread.ts / events.ts / exec.ts
│   │                            → @openai/codex-sdk
│   ├── python/                  src 21 个 py + 16 组示例（quickstart→流式→login→…）+ notebooks
│   └── python-runtime/
│
├── codex-cli/                   旧版 Node 外壳：现在主要是 npm 分发入口（bin/）
├── docs/                        文档：sandbox.md / execpolicy.md / skills.md / config.md /
│                                slash_commands.md / authentication.md / agents_md.md…
├── scripts/ tools/ patches/     构建与 CI 基建（Python 打包脚本、bazel 补丁、mock server）
├── bazel/ MODULE.bazel justfile flake.nix pnpm-workspace.yaml  多套构建系统并存
└── AGENTS.md / README.md / CHANGELOG.md / SECURITY.md
```

## 怎么读这棵树（对照你已有的 deepagents 知识）

| 你熟悉的（deepagents） | codex 这边的对应物 |
|---|---|
| agent loop 全委托 langgraph | loop 自己手写：`core/src/session/turn.rs` 的 `run_turn` |
| 四个中间件检查站 | `hooks/` 钩子引擎（engine + declarations + config_rules） |
| checkpoint 自动存档 | `rollout/`（JSONL）+ `state/`（SQLite），接口在 `thread-store/` |
| SubAgentSdk | `core/src/agent/` 子代理 + `ext/agent-message-board/` 消息板 |
| 虚拟文件系统沙箱 | 真沙箱六件套：sandboxing / execpolicy / linux / windows / mxc / network-proxy |

三个反直觉点：

1. **壳比引擎大**：tui 一个 crate 43 万行，是 core（24.5 万行）的 1.75 倍。codex 的复杂度大头在交互层，不在 agent loop。
2. **模型层最薄**：仓库里没有任何模型，只有客户端（⑤ 层合计约 4.7 万行，占总量 3%）。接第三方端点改 `model-provider` 一处。
3. **协议是独立 crate**：`protocol/` 把"壳↔引擎"的合同单独抽出来，所以 tui / exec / app-server 三个壳可以互不知晓地共用同一个 core。
