# -*- coding: utf-8 -*-
"""链路比较、扩展比较、结构性差异、共性模式、取舍数据。"""

FLOW_COMPARISONS = [
    {
        "topic": "tool-call 工具调用链路",
        "summary": "六家的链路骨架同构(解析→闸→分派→执行→截断/规范→回填→续轮),但『闸』的位置与数量差异极大:codex 有 execpolicy+三级审批双闸再进 OS 沙箱;hermes 策略链+人审门;openai-agents 可选 needs_approval 中断;pi 只有可 block 的 beforeToolCall 钩子;claude-code-sdk 仅对 SDK MCP 工具进程内分派(内置工具链路在闭源 CLI);langgraphjs 无闸,异常默认回喂模型。",
        "per_project": [
            {"project_id": "codex", "status": "implemented",
             "summary": "模型响应→build_tool_call 解析→execpolicy 规则判定→三级审批(hooks→Guardian→用户,fail-closed)→FuturesOrdered 并行分派→沙箱内执行→输出截断→RespondToModel/回填→needs_follow_up 决定续轮。",
             "refs": ["flow:fl-tool-call"]},
            {"project_id": "claude-code-sdk", "status": "partial",
             "summary": "SDK 侧仅两条子链:can_use_tool 审批控制链(CLI 请示→SDK 回调→回执)与 SDK MCP 工具执行链(JSON-RPC 转发→SdkMcpBridge→jsonschema 校验→run_tool);内置工具的完整链路在闭源 CLI,不可审计。",
             "refs": ["flow:fl-sdk-mcp", "flow:fl-permission-approval"]},
            {"project_id": "pi", "status": "implemented",
             "summary": "toolCall→prepareToolCall(按名查找+参数校验)→beforeToolCall(可 block)→并行/串行执行(signal 可取消,onUpdate 流进度)→afterToolCall 覆写→toolResult 回填;stopReason=length 时整批判失败防截断参数被执行。",
             "refs": ["flow:fl-tool-call"]},
            {"project_id": "openai-agents", "status": "implemented",
             "summary": "process_model_response 九类分类→execute_tools_and_side_effects 分派;函数工具 invoke 前过 needs_approval(未决则 Interruption 保存 RunState)→asyncio.to_thread/协程执行→结果/异常回填(错误也转 ToolOutput)→RunAgain 续轮。",
             "refs": ["flow:fl-tool-call"]},
            {"project_id": "hermes", "status": "implemented",
             "summary": "normalize 出 tool_calls→run_tool_round 校验→_execute_tool_calls 分段(并行安全段/顺序屏障)→_dispatch_authorized_once 策略链(危险命令走容器 fast-path→floors→yolo→allowlist→模式检测→人审门)→registry.dispatch→结果规范化回填;执行前强制落库。",
             "refs": ["flow:fl-tool-call"]},
            {"project_id": "langgraphjs", "status": "implemented",
             "summary": "节点输出中的 tool_call→ToolNode.run 提取→runTool 按名查找→tool.invoke({tool_call, ToolRuntime})→Promise.all 并发→收敛为 ToolMessage/Command 写回 messages channel→下个超步由版本触发 callModel;无权限/沙箱/截断检查点。",
             "refs": ["flow:fl-tool-call"]}
        ]
    },
    {
        "topic": "checkpoint-resume 可恢复性",
        "summary": "三种实现学派:快照派(langgraphjs 每超步全量快照+interrupt/resume 协议;openai-agents RunState 序列化含审批)对账派(hermes persist-before-execute+turn 租约;claude-code-sdk SessionStore 镜像+物化)与重放派(pi 会话树重放活跃路径;codex 历史 fork 新线程)。",
        "per_project": [
            {"project_id": "codex", "status": "partial",
             "summary": "无可恢复执行快照;resume=重放 rollout JSONL 重建会话,fork=从历史克隆新线程(thread id 变更+不可变文件);崩溃点续跑不支持。",
             "refs": ["node:ROLLING"]},
            {"project_id": "claude-code-sdk", "status": "implemented",
             "summary": "transcript_mirror 批量镜像(500 条/1MiB)到外部 SessionStore→store→本地物化→CLI --resume;恢复语义=会话重放,非执行栈。",
             "refs": ["flow:fl-store-resume"]},
            {"project_id": "pi", "status": "implemented",
             "summary": "JSONL 树 leaf 指针决定活跃分支,resume=buildContextEntries/buildSessionProjection 重放;CompactionEntry 作为可回退上下文检查点;非运行时快照。",
             "refs": ["flow:fl-session-resume"]},
            {"project_id": "openai-agents", "status": "implemented",
             "summary": "NextStepInterruption→RunState.to_json($schemaVersion 1.18,含未决审批与 pending_input)→人工处理→from_string 续跑;run 内锁冲突亦有 rewind 快照。",
             "refs": ["node:RUNSTATE"]},
            {"project_id": "hermes", "status": "implemented",
             "summary": "persist-before-execute(append 失败即终止轮)+跨进程 durable turn 租约:resume 时以持久 transcript 对账已执行块,保证必见已执行副作用;shadow git 另管文件回滚。",
             "refs": ["flow:fl-session-resume"]},
            {"project_id": "langgraphjs", "status": "implemented",
             "summary": "interrupt() 写入断点坐标+RESUME channel→每超步 _putCheckpoint 全量快照→Command{resume} 从 checkpoint 重建 channels 重放 pendingWrites 续跑;TS 独有 responseSchema 校验恢复值。",
             "refs": ["flow:fl-interrupt-resume"]}
        ]
    },
    {
        "topic": "error-retry 错误与重试",
        "summary": "模型调用重试普遍集中在 client/provider 层并带退避与限流分类;上层策略分化:codex 采样重试小环+provider 建议采纳、openai-agents get_response_with_retry+rewind 回卷、hermes 双层(供应商正则分类器+会话级 _prepareRetry,溢出改走 compact-and-retry)、pi 双层(供应商级+会话级)、langgraphjs 引擎不管(委托模型层/用户节点逻辑)、claude-code-sdk 全在 CLI(SDK 只见错误帧)。",
        "per_project": [
            {"project_id": "codex", "status": "implemented",
             "summary": "内环 run_sampling_request 的小重试环:按 provider 重试配置与响应建议(如 Retry-After)退避;terminal_error 才上抛外环。",
             "refs": ["flow:fl-error-retry"]},
            {"project_id": "claude-code-sdk", "status": "delegated",
             "summary": "模型/工具失败分类与重试全在闭源 CLI;SDK 侧仅见 result error 帧与错误消息,无策略面。",
             "refs": []},
            {"project_id": "pi", "status": "implemented",
             "summary": "双层重试:pi-ai 供应商级 retryProviderRequest(正则分类器判可重试)+coding-agent 会话级 _prepareRetry;上下文溢出在会话层显式排除改走 compact-and-retry。",
             "refs": ["flow:fl-error-retry"]},
            {"project_id": "openai-agents", "status": "implemented",
             "summary": "get_response_with_retry:重试策略+provider 建议结合,失败时 rewind 回卷会话状态再试;MaxTurnsExceeded 等运行错误可被 error_handlers 转为输出。",
             "refs": ["flow:fl-error-retry"]},
            {"project_id": "hermes", "status": "implemented",
             "summary": "双层:供应商级正则分类器判定可重试错误+runtime fallback 热切换;会话级 _run_api_retry_loop/_prepareRetry;上下文溢出显式排除改走 compact-and-retry;外层异常超 8 次兜底终止。",
             "refs": ["flow:fl-error-retry"]},
            {"project_id": "langgraphjs", "status": "delegated",
             "summary": "引擎无模型重试策略;节点内异常默认传播(ToolNode 例外:工具错误回喂模型让模型自纠);重试语义委托 @langchain/core 或用户节点。",
             "refs": []}
        ]
    }
]

EXTENSION_COMPARISONS = [
    {
        "topic": "添加一个自定义工具",
        "summary": "六条路径:openai-agents 装饰器(@function_tool 自动 schema+pydantic 校验)、pi/hermes 注册 API 或落文件、claude-code-sdk 进程内 MCP(@tool)、codex 宿主动态注入或 MCP 配置、langgraphjs 直接把 LangChain tool 塞给 ToolNode。schema 生成方式与校验责任是主要差异。",
        "per_project": [
            {"project_id": "codex", "status": "implemented",
             "summary": "两条路:宿主动态注入(应用层经 thread 请求注入 CustomTool/FunctionTool)或 mcp_servers 配置接外部 server;核心内置工具为 Rust 硬编码,第三方不进内核注册表。",
             "refs": ["extension:ep-dynamic-tools", "extension:ep-mcp-servers"]},
            {"project_id": "claude-code-sdk", "status": "implemented",
             "summary": "@tool 装饰器+create_sdk_mcp_server 生成进程内 MCP server,经 initialize 下发 type='sdk' 配置;CLI 调用时 JSON-RPC 回 SDK 执行。",
             "refs": ["extension:ep-sdk-mcp-tool"]},
            {"project_id": "pi", "status": "implemented",
             "summary": "registerTool(api,tool) 注册:TypeBox 定义 schema,执行前后各有钩子;扩展模块经 jiti 从目录加载,40+ 事件可变换行为。",
             "refs": ["extension:ep-tools", "extension:ep-plugin"]},
            {"project_id": "openai-agents", "status": "implemented",
             "summary": "@function_tool 装饰器从函数签名+docstring 自动生成 JSON schema,pydantic 校验参数;也支持手写 FunctionTool;MCP 工具经 MCPServer 聚合。",
             "refs": ["extension:ep-function-tool", "extension:ep-mcp-server"]},
            {"project_id": "hermes", "status": "implemented",
             "summary": "tools/*.py 落文件即注册(声明式目录发现)+插件 register(ctx) 注册+MCP 动态汇聚;参数校验在 run_tool_round。",
             "refs": ["extension:ep-tool-registration", "extension:ep-plugin-system"]},
            {"project_id": "langgraphjs", "status": "implemented",
             "summary": "把任意 LangChain tool(BaseTool/函数 tool)传入 createReactAgent({tools}) 或 ToolNode;schema/校验全部委托 @langchain/core 工具定义。",
             "refs": ["extension:ep-tools"]}
        ]
    },
    {
        "topic": "接入一个新模型供应商",
        "summary": "光谱两端:pi 要写 Provider+协议适配(自由度最大),codex 只需一段配置(但必须说 Responses 协议);openai-agents 实现 Model/ModelProvider ABC 或直接借道 litellm/any-llm 前缀路由;hermes 写 Profile+adapter 归一到 chat.completions;langgraphjs 零工作(@langchain/core 已有的模型直接注入);claude-code-sdk 无入口(env 决定)。",
        "per_project": [
            {"project_id": "codex", "status": "implemented",
             "summary": "config.toml model_providers 加配置块(base_url/env_key/重试/WS),新 provider 必须兼容 Responses API;chat 协议被显式拒绝。",
             "refs": ["extension:ep-model-providers"]},
            {"project_id": "claude-code-sdk", "status": "delegated",
             "summary": "SDK 无 provider 扩展点(设计上 absent);供应商选择=CLI 读 env(ANTHROPIC_BASE_URL/Bedrock/Vertex/Foundry),SDK 只透传。",
             "refs": []},
            {"project_id": "pi", "status": "implemented",
             "summary": "registerProvider 或扩展包:实现 Provider 接口(目录+stream),或复用既有协议适配器(anthropic/openai/google/bedrock/mistral)只补模型目录。",
             "refs": ["extension:ep-provider"]},
            {"project_id": "openai-agents", "status": "implemented",
             "summary": "实现 Model+ModelProvider ABC 注册到 RunConfig.model_provider;或零代码借道 MultiProvider 前缀路由 litellm('litellm:...')/any-llm。",
             "refs": ["extension:ep-model-provider"]},
            {"project_id": "hermes", "status": "implemented",
             "summary": "写 ProviderProfile+resolve_provider_client 分支(或 *_adapter 归一);内部恒为 chat.completions 总线,Anthropic messages 等在入口转换。",
             "refs": ["extension:ep-provider-profile"]},
            {"project_id": "langgraphjs", "status": "delegated",
             "summary": "本仓无 provider 层:@langchain/core 已支持的模型直接传入 llm 参数即可;新供应商=在 @langchain/core 生态实现 ChatModel,引擎零改动。",
             "refs": ["extension:ep-model"]}
        ]
    }
]

ARCHITECTURAL_DIFFERENCES = [
    {
        "id": "d1-loop-morphology",
        "title": "循环形态学:谁推动下一步",
        "summary": "六个项目给出了 agent loop 的五种形态:模型输出驱动的 while(codex/pi/openai-agents)、phase 状态机(hermes)、BSP 数据流超步(langgraphjs)、消息泵委托(claude-code-sdk)。langgraphjs 是唯一『循环不由模型输出直接决定』的——继续与否由 channel 版本触发;claude-code-sdk 是唯一『循环不可审计』的——在闭源 CLI。",
        "significance": "major",
        "per_project": [
            {"project_id": "codex", "statement": "双环:任务环(RegularTask::run)包采样环(run_turn),模型输出经 needs_follow_up 驱动,无轮数上限。"},
            {"project_id": "claude-code-sdk", "statement": "消息泵:SDK 只路由 stream-json 帧,循环语义全部在闭源 CLI。"},
            {"project_id": "pi", "statement": "双 while 内核(约140行)+9 回调注入:循环本体零策略。"},
            {"project_id": "openai-agents", "statement": "while True + next_step 四态数据类:显式状态机混合形态。"},
            {"project_id": "hermes", "statement": "while + 约20个 phase 模块反射读写 _LoopState:状态机管线化。"},
            {"project_id": "langgraphjs", "statement": "Pregel BSP 超步:while(await loop.tick()),继续与否由 channel 版本触发,模型调用只在节点内。"}
        ]
    },
    {
        "id": "d2-trust-boundary",
        "title": "信任边界:权限与沙箱的纵深梯度",
        "summary": "隔离强度构成完整光谱:codex(应用层 execpolicy+三级审批 fail-closed,下探 OS 沙箱四平台统一收口)→hermes(进程内策略链+可选六种 OS 隔离后端,自认非 containment)→openai-agents(工具级 needs_approval+opt-in 沙箱框架)→claude-code-sdk(判定在闭源 CLI,SDK 回调+遮蔽告警)→pi(显式放弃,唯一 beforeToolCall 钩子+容器化指引)→langgraphjs(引擎完全无判定无沙箱)。",
        "significance": "critical",
        "per_project": [
            {"project_id": "codex", "statement": "双链纵深:规则→审批→OS 强制,唯一默认启用不可绕过沙箱的项目。"},
            {"project_id": "claude-code-sdk", "statement": "黑盒判定+回调宿主;SDK 甚至复刻规则解析器来告警 can_use_tool 被遮蔽。"},
            {"project_id": "pi", "statement": "安全=部署问题:beforeToolCall 是唯一强制点,官方推荐容器化三方案。"},
            {"project_id": "openai-agents", "statement": "默认全放行:needs_approval 逐工具声明,opt-in 沙箱框架接七家远端。"},
            {"project_id": "hermes", "statement": "进程内防线丰富但官方自述非 containment;默认 local 后端直跑宿主机(security/major)。"},
            {"project_id": "langgraphjs", "statement": "引擎路径无权限无沙箱:ToolNode 从查找到 invoke 零检查,责任全在应用。"}
        ]
    },
    {
        "id": "d3-persistence-families",
        "title": "持久化形态学:三个家族",
        "summary": "JSONL 追加系(codex rollout 可重放、pi 会话树分支一等公民、claude transcript 镜像)、SQLite/DB 系(hermes 自研全栈 WAL+FTS5+36 个加固模块、openai-agents Session 协议五后端)、快照系(langgraphjs 每超步全量 channel 快照+durability 档位)。只有 langgraphjs 持久化执行状态而非消息。",
        "significance": "major",
        "per_project": [
            {"project_id": "codex", "statement": "rollout JSONL(不可变,append-only)+sqlite state DB 双轨。"},
            {"project_id": "claude-code-sdk", "statement": "镜像而非权威:CLI 拥有 transcript,SDK 批量镜像到 SessionStore。"},
            {"project_id": "pi", "statement": "JSONL 树(id/parentId+leaf):唯一把分支/rewind 做成一等公民的持久化。"},
            {"project_id": "openai-agents", "statement": "Session 协议多后端(SQLite 内置+Redis/Mongo/SQLAlchemy/服务端),轮末集中写。"},
            {"project_id": "hermes", "statement": "自研 SQLite 全栈+persist-before-execute:持久化优先于副作用。"},
            {"project_id": "langgraphjs", "statement": "checkpointer 快照即持久化:checkpoint/unit=图状态+跨 thread store 记忆。"}
        ]
    },
    {
        "id": "d4-model-layer",
        "title": "模型层厚薄光谱",
        "summary": "pi 自带 40+ provider 与多协议适配器(最厚);openai-agents 双层 ABC+litellm/any-llm 前缀路由;hermes Profile+中央路由统一到 chat.completions 总线;codex 配置级单协议(Responses,chat 显式拒绝);langgraphjs 结构类型委托 @langchain/core;claude-code-sdk 无模型层(env 透传)。",
        "significance": "major",
        "per_project": [
            {"project_id": "codex", "statement": "协议统一优先:全部 provider 说 Responses,配置级抽象无 trait。"},
            {"project_id": "claude-code-sdk", "statement": "零模型层:温度等参数都不可达,供应商由 env 决定。"},
            {"project_id": "pi", "statement": "最厚:Provider/Models/Model<TApi> 全栈+多协议适配+运行时 setProvider。"},
            {"project_id": "openai-agents", "statement": "Model/ModelProvider ABC+MultiProvider 前缀路由,Responses 原生/ChatCompletions 转换。"},
            {"project_id": "hermes", "statement": "ProviderProfile 声明面+resolve_provider_client 中央路由,内部 chat.completions 总线。"},
            {"project_id": "langgraphjs", "statement": "零自有抽象:LanguageModelLike+bindTools 结构类型,委托 @langchain/core。"}
        ]
    },
    {
        "id": "d5-subagent-spectrum",
        "title": "子智能体五种实现与一个缺席",
        "summary": "codex 全功能子线程(独立 Session/rollout,审批强制 Never)、claude CLI Task 工具(SDK 管在飞账本)、openai-agents as_tool 嵌套 run+handoff 换手、hermes delegate_task(独立 SessionDB+工具裁剪+心跳/steer/worktree)、langgraphjs subgraph/Send+supervisor 预制件;pi 完全缺席(官方姿势=自定义工具内嵌套调用)。",
        "significance": "major",
        "per_project": [
            {"project_id": "codex", "statement": "spawn_agent 启动完整子 Codex 线程,消息板通信,spawn 边入图存储。"},
            {"project_id": "claude-code-sdk", "statement": "CLI Agent 工具派生;SDK 维护 task 账本,后台子代理延迟 run 结束。"},
            {"project_id": "pi", "statement": "absent:多 LLM 调用靠自定义工具内 streamSimple,无隔离无聚合。"},
            {"project_id": "openai-agents", "statement": "as_tool=真子上下文委派,handoff=对话权转移(历史折叠);同轮多 handoff 只执行首个。"},
            {"project_id": "hermes", "statement": "delegate_task 派生全新 AIAgent:独立 SessionDB+阻断工具集+心跳+steer+可选 worktree。"},
            {"project_id": "langgraphjs", "statement": "子图作节点+Send map-reduce+supervisor/swarm 预制件;隔离=checkpoint 命名空间。"}
        ]
    },
    {
        "id": "d6-project-taxonomy",
        "title": "项目类型谱系:SDK→引擎→产品",
        "summary": "六个项目覆盖了 agent 技术栈的完整生态位:薄协议 SDK(claude-code-sdk,26/55 自实现)→纯库 SDK(openai-agents,52/55)→极简内核+插件(pi,43/55,但大量 absent-by-design)→图引擎(langgraphjs,30/55 自实现+13 委托)→全栈 harness(hermes,54/55)→产品级 CLI+SDK(codex,55/55)。自实现率与『开箱即可用』正相关,与『可嵌入性』负相关。",
        "significance": "info",
        "per_project": [
            {"project_id": "codex", "statement": "产品级:CLI+TUI+app-server+TS SDK,130+ crate 全栈自包含。"},
            {"project_id": "claude-code-sdk", "statement": "薄 SDK:28/55 委托闭源 CLI,卖点是 CLI 能力的 API 化。"},
            {"project_id": "pi", "statement": "极简内核:循环/模型/工具内建,权限/子代理/MCP 显式不做,扩展经进程内 TS 插件。"},
            {"project_id": "openai-agents", "statement": "纯库 SDK:无 CLI/HTTP 入口,Agent=LLM+instructions+tools+handoffs。"},
            {"project_id": "hermes", "statement": "全栈 harness:循环/学习循环/记忆/审批/多后端全自研,单进程产品。"},
            {"project_id": "langgraphjs", "statement": "图引擎:模型/工具/权限全外部,卖点是可恢复执行+HITL+编排组合。"}
        ]
    }
]

COMMON_PATTERNS = [
    {
        "id": "c1-streaming-events",
        "title": "事件化流式输出全员标配",
        "summary": "六个项目都实现了统一的流式事件模型与增量 token 产出(obs.streaming-events 全部 implemented):codex Event/Notification 协议、claude stream-json 帧、pi 归一 StreamEvent、openai-agents 流式 RunEvent、hermes event_callback、langgraphjs StreamMode duplex stream。流式已是 harness 层事实标准。"
    },
    {
        "id": "c2-tool-call-round",
        "title": "『工具调用→回填→续轮』核心轮驱动",
        "summary": "五家的循环由『模型响应是否含工具调用』直接驱动;唯一例外 langgraphjs 由 channel 版本触发(工具调用只是节点间数据)。回填形态一致:工具结果序列化为消息(ToolMessage/toolResult/tool role)进历史后再次采样。"
    },
    {
        "id": "c3-usage-accounting",
        "title": "用量记账全员实现",
        "summary": "六家都在模型层做 token/费用累计并暴露(model.usage-accounting 全部 implemented):pi Model 元数据带价目、hermes 账本落库、openai-agents usage 聚合进 RunContext、codex 事件携带 token 计数、langgraphjs 委托 @langchain/core 但 ToolRuntime 可见、claude SDK 镜像 usage 帧。"
    },
    {
        "id": "c4-cancel-propagation",
        "title": "取消信号统一传播到执行面",
        "summary": "六家都实现了取消传播(lifecycle.cancel 全部 implemented):AbortSignal/Rust CancellationToken/asyncio 任务取消都会传到子进程或工具执行;codex TurnAborted 贯穿两环、pi signal 传入 tool.execute、langgraphjs config.signal 可中止图、claude SDK interrupt 控制请求。"
    },
    {
        "id": "c5-mcp-standard",
        "title": "MCP 成为工具扩展事实标准(4/6)",
        "summary": "codex(mcp_servers 配置+rmcp-client)、openai-agents(MCPServer 聚合)、hermes(MCP client 接入)、claude-code-sdk(外部 MCP 配置+进程内 SDK MCP)四家原生实现;pi 显式拒绝(absent,走进程内 TS 扩展);langgraphjs 核心不集成(应用可经 LangChain 适配)。"
    },
    {
        "id": "c6-declarative-tools",
        "title": "工具=名称+schema+执行函数的三元组",
        "summary": "六家的工具声明面同构(TypeBox/pydantic/zod/JSON Schema 各选其一),差异只在 schema 生成自动化程度:openai-agents/claude(@tool) 从函数签名自动生成,pi 用 TypeBox 手写,langgraphjs 委托 LangChain 定义,hermes/codex 各有声明格式。"
    }
]

TRADEOFFS = [
    {"id": "t-codex", "project_id": "codex", "title": "安全纵深 vs 协议锁定与复杂度",
     "summary": "唯一的四平台 OS 沙箱+三级 fail-closed 审批,安全最强;代价是模型协议锁死 Responses(无法接 ChatCompletions-only 供应商)、130+ crate 的维护面、审批模式组合的认知成本。"},
    {"id": "t-claude-code-sdk", "project_id": "claude-code-sdk", "title": "集成速度 vs 控制力",
     "summary": "绑定闭源 CLI 换来零循环开发与 CLI 全部能力(子代理/hooks/checkpoint)即开即用;代价是循环语义/上下文管理/模型参数不可控、升级需同步核对 CLI 版本、SDK 行为黑盒只能靠镜像与告警补偿。"},
    {"id": "t-pi", "project_id": "pi", "title": "极简可审计 vs 功能真空",
     "summary": "140 行循环+JSONL 树+进程内插件,代码可全量心算;代价是无权限/无沙箱指引之外的任何防线、无子代理、无 MCP,多智能体与安全场景全部自建。"},
    {"id": "t-openai-agents", "project_id": "openai-agents", "title": "功能均衡 vs 巨型函数与默认放行",
     "summary": "HITL RunState/handoff/guardrail/tracing/沙箱框架齐备;代价是 _run_impl 约 1660 行巨型函数回归面大、主循环无自动上下文预算、非沙箱工具默认进程内裸执行。"},
    {"id": "t-hermes", "project_id": "hermes", "title": "能力最全 vs 可审计性",
     "summary": "学习循环/记忆/审批/多后端/委派运维全家桶,persist-before-execute 崩溃一致性最强;代价是 phase 反射状态机数据流不可静态直读、进程内防线自认非 containment、默认后端直跑宿主机。"},
    {"id": "t-langgraphjs", "project_id": "langgraphjs", "title": "引擎通用性 vs agent 语义外包",
     "summary": "BSP 超步+每超步快照带来最强恢复/时间旅行/HITL;代价是模型/工具/权限/重试全部外包给 @langchain/core 与应用,裸引擎不是 agent,缺省行为(工具异常回喂)可能掩盖错误。"}
]
