# 我们逐行审计了 8 个 Agent 框架的源码,发现所有人在写同一个 5 行循环

> 覆盖:OpenAI Codex(Rust)· Claude Agent SDK(Python)· OpenAI Agents SDK · Pi · Hermes · LangGraph.js · DeepSeek Harness(TS)· deepagents(langchain-ai,Python)
> 方法:55 个统一架构概念 × 逐行取证,每条结论落到 file:line,产出 8 份单项目审计 + 1 份六方对比报告(DSH、deepagents 为独立审计,未入对比矩阵)

## 一、先说扎心的:所有 Agent 框架的内核只有 5 行

扒掉八家的营销外衣,核心循环一模一样:

```python
while True:
    回复 = 调用模型(历史消息)
    if 回复里没有工具调用: break   # 模型认为干完了
    结果 = 执行工具(回复里的工具调用)
    历史消息.append(结果)
```

整个行业的竞争,不是在发明新循环,而是在回答一个问题:**这 5 行代码放进什么壳里,允许你从哪里伸手进去改。**

## 二、六种壳:主循环形态学

| 框架 | 循环形态 | 一句话 |
|---|---|---|
| LangGraph | Pregel 图 superstep | 你画流程图,引擎替你转圈(`pregel/index.ts:2613`) |
| deepagents | 图+中间件栈 | 约 700 行装配:middleware 栈+子代理+权限→HITL 合并后交给 langgraph 转(`graph.py:277`);自研在装配与上下文工程,循环是别人的 |
| OpenAI Agents SDK | 单 while·四态 | 每轮吐一张"下一步"纸条:完成/换人/继续/暂停(`run.py:987`) |
| Pi | 双 while·9 回调 | 140 行读完整个循环,行为全靠 9 个插槽注入(`agent-loop.ts:162`) |
| DeepSeek Harness | 三层 while·waterfall | kick/turn/step 三层套娃,循环不是特权内核——每个决策点都是可拦截事件(`packages/core/agent-loop/src/agent.ts`) |
| Hermes | phase 状态机 | 一轮拆 20 个工位流水线,传同一本大账本(`conversation_loop.py:1636`) |
| Claude SDK | 闭源·消息泵 | 循环在闭源 CLI 里,你的代码只是传菜员(`query.py:388`) |
| Codex | 内环+外环 | 外环管任务内环管采样,审批沙箱焊死在循环体(`regular.rs:104` / `turn.rs:426`) |

规律:**越通用的引擎,循环离"agent"越远、越可编程;越贴近产品,循环和策略咬得越紧、越改不动。** Claude SDK 是极端——干脆放弃循环所有权,换即插即用。

## 三、四个行业共识(很多人还没意识到)

**1. append-only 日志成了持久化共识。** Codex 的 rollout JSONL 注释原文就是"so sessions can be replayed";Pi 走得更远,每条记录带父指针,分支/回滚零复制;连 revert 都不删旧文件,新建不可变文件封存。

**2. 压缩(compaction)是产品标配,SDK 稀缺。** Pi 阈值触发、Hermes 每轮预检门、Codex mid/post 双时机、Claude 闭源自动——而 OpenAI Agents SDK 和 LangGraph 明确"自己造"。

**3. 多 Agent 全走隔离派发。** 没有一家是"同一对话里换角色"——都是独立上下文的新执行体:Codex 开完整子线程(独立 Session/rollout)、Hermes 的 delegate_task 连工具集都裁剪、OpenAI SDK 的 as_tool 嵌套独立 run。

**3.5 记忆的两种哲学。** Hermes 最激进:每轮结束自动 fork 子 agent 回看对话,把值得记的沉淀成 skill/memory;DeepSeek Harness 最克制:把"隐式长期记忆"判为设计上不提供,给四种显式替代(spill 工具结果外置 / skill 技能注册表 / todo-goal 持久计划 / 跨会话有界引用)——不自动记,但每一笔都可控。

**4. 一切在为 prompt cache 服务。** 这是前三个共识的总开关:缓存按"从第 0 字节起的最长公共前缀"命中——所以历史只能追加不能截断(截头=每轮全量缓存 miss),压缩是"偶尔付一次学费换几百轮命中",子代理隔离是为了不污染主前缀。Hermes 连学习循环都要注明"主对话与 prompt cache 不被触碰"。

## 四、最大的分化:安全光谱

六个项目恰好构成隔离强度的完整梯度:

```
Codex ──── DSH ──── Hermes ──── OpenAI SDK ≈ deepagents ──── Claude SDK ──── Pi ──── LangGraph
```

- **Codex**:唯一双层齐全——应用层(execpolicy 规则+三级审批,八态 fail-closed)之下还有 OS 级沙箱(Seatbelt/Landlock/bwrap/Windows 受限令牌),默认启用不可绕过;
- **DeepSeek Harness**:权限也是双层——tools/pre-execute 策略瀑布(可允许/拒绝/转审批)+ 任何 guard 可拒、无人能强行放行的单调 guard;沙箱三档(read-only/workspace-write/danger-full-access),请求档位不可用时 fail-closed 抛 SANDBOX_UNAVAILABLE 而非裸跑;
- **deepagents**:文件权限是真的(FilesystemPermission 首匹配 deny/interrupt,自动装配 HITL 中断),但只覆盖内置文件工具层——LocalShellBackend 用 `shell=True` 直跑宿主且不被权限管,文档自认无隔离;沙箱靠 opt-in 的远端后端;
- **Hermes**:进程内审批门很丰富,但官方自认"非 containment",默认后端直跑宿主机;
- **OpenAI SDK**:工具默认逐个 opt-in 审批,不声明就直接在宿主进程裸跑;
- **Claude SDK**:六种权限模式+can_use_tool 回调,但判定逻辑在闭源 CLI;
- **Pi**:显式不设防,官方文档教你去用 Docker;
- **LangGraph**:引擎路径上查不到任何 allow/deny,连沙箱概念都没有。

**框架的安全默认值,就是它对你的真实态度:产品假设用户不懂风险,框架假设开发者责任自负。**

**横评星表(★ 多 = 好):**

| | 改循环容易度 | 省心度 | 安全默认 | 可审计性 |
|---|---|---|---|---|
| LangGraph | ★★★★★ | ★☆ | ★☆(自己搭) | ★★★★ |
| deepagents | ★★★★(middleware) | ★★★ | ★★(shell 无隔离) | ★★★ |
| OpenAI SDK | ★★(别改) | ★★★★ | ★★☆ | ★★★ |
| Pi | ★★★(插槽内) | ★★ | ★☆(自己搭) | ★★★★★ |
| DSH | ★★★★(事件) | ★★★ | ★★☆ | ★★ |
| Hermes | ★☆(改源码) | ★★★★ | ★★☆(默认危险) | ★☆ |
| Claude SDK | ☆(黑盒) | ★★★★★ | ★★★☆(黑盒保证) | ★ |
| Codex | ★☆(焊死) | ★★★★ | ★★★★★ | ★★★ |

规律就一条:**"可改造性"和"省心/安全"基本是跷跷板**——Codex/Claude 把循环锁得最死所以最省心最安全,LangGraph/Pi 把循环交出来所以最灵活但什么都要自己负责。选型前先问自己:你要的是"用"(选右边几列),还是"改"(选左边几列)?

## 五、选型就三个问题

**1. 造什么车?** 编码/研发提效工具 → 直接用 Codex / Claude Code 成品;领域助手 → 可编程 SDK;多 agent + 重审批工作流 → LangGraph(checkpoint+interrupt 是审批流的最好底座,但代价要认清:引擎世界观是"节点/边/channel",agent 常识要自己翻译成图——reducer、条件边、恢复语义都得真正学懂,且安全层纯自建);想要"一切皆插件、每请求路由供应商"的极客底座 → DeepSeek Harness(cordis 事件系统,adapter 按请求解冻,但社区生态小)。

**2. 用什么模型?协议兼容已不是障碍,但端点只管四层里的第一层。**

2026 年的真实玩法是**厂商抢着建翻译亭**:智谱官方提供 Responses 兼容端点,Codex 填三行配置就能用 GLM——

```toml
[model_providers.zhipu]
base_url = "https://open.bigmodel.cn/api/v1"
wire_api = "responses"   # Codex 一个字没变,是智谱学会了它的语言
```

DeepSeek 同样建了 Anthropic 兼容端点接 Claude Code。翻译层有三个位置,按"坏了谁修"排序:**框架自带(OpenAI SDK 的 Converter/litellm)> 厂商服务端(智谱/DeepSeek,商业动机+专业团队)> 自建代理(坏了只能自己修)**——生产环境只用前两种。

但"协议通"只是四层中的第一层,上线前把另外三问问完:**特性全不全**(思考块、缓存标记常只仿真了子集,静默失效)/ **干得好不好**(CLI 的 prompt 和节奏为自家模型调校,换模型=换演员读同一剧本,端点无解)/ **升级跟不跟**(CLI 用新协议特性→厂商仿真有时间差)。**答案质量 = 模型能力 × 调校匹配 × 翻译保真度,三者相乘**;分不清哪项拖后腿时,做对照实验:同一模型走兼容端点 vs 走原生 SDK,跑同一组任务。

最后一条,优先级高于一切选型争论:**框架类(OpenAI Agents SDK / LangGraph / Pi)默认全放行——OpenAI SDK 的审批要逐工具 opt-in,LangGraph 的引擎路径上根本没有权限判定点**。工具参数是模型生成的,一次提示注入就能让默认路径直接执行危险调用。所以上线前先花两天给工具执行套容器或自建审批层:选错框架顶多返工,安全默认出事是数据泄露——产品系(Codex/Claude)的防线是默认焊死的,框架系的责任自负,这是两类项目的本质区别。

**选型还差两块垫片:**

**地基 vs 素材库。** 一个框架能不能当地基,三条标准:**语言贴你的管线**(团队是 Python 就别选逼你写 TS 的)、**你能读懂能修**(出事时看得懂它的循环吗)、**领域对口**(它带的手牌是你的活吗——编码 agent 的刀再快,也切不了你的爬虫→MySQL→LLM→报告流水线)。三条全中才能当地基;只中一两条的当素材库——把它的好设计(事件溯源日志、压缩时机、多后端派发)抄进自己项目,别把整栋房子搬回来。按这三条,deepagents 对 Python 团队几乎全中(纯 Python、基于 langgraph 生态、通用 agent 领域),DSH 对 Python 团队三条全不中——这就是同一家公司的两个候选,命运完全不同的原因。

**错位五处自查。** 把产品型 harness 硬嵌进异构技术栈,疼点高度集中在五处:①错误变量(跨进程后异常只剩 exit code,自己发明 JSON 协议往回传);②记账断两截(LLM 调用不走你的网关,成本要记两套);③定制要写它的语言(想改重试/压缩/记忆策略,得用它的栈);④双栈维护(Node+pip 两套依赖两套环境);⑤领域不对口(它的内置工具全为"程序员写代码"设计)。中两条以上,别硬娶。

**想拿产品当框架?只有 Codex 给了这条路(Apache 2.0 真开源;Claude 底层闭源,SDK 只是壳,没有此选项):**

| 选项 | 定制性 | 安全底子 | 维护成本 |
|---|---|---|---|
| Codex 姿势 2(app-server 协议嵌入) | 中(协议面可编程) | ★★★★★(白拿) | 低(跟官方升级) |
| Codex fork 改内核 | 高 | ★★★★★ | 极高(自己背安全补丁) |
| pi / OpenAI SDK / LangGraph | 高(纯框架) | ☆ 要自建 | 低~中 |

一句话:要 Codex 的安全,用嵌入别 fork;要"自己的框架",拿 pi 或 OpenAI Agents SDK/LangGraph 这种天生为被改造而生的开源底座,把产品里学到的设计(双环结构、审批 fail-closed、沙箱收口)当蓝图移植过去。

**全文收拢成一句:claude-agent-sdk 和 codex 是整车,直接开走;openai-agents-python 和 langgraph 是发动机,自己造车——先想清楚你要整车还是发动机,再回来翻报告对细节。**

## 六、审计报告怎么用

本次产出(全部 validator 零错误,行号逐一到源码核实):

- `agent-code-atlas-output/<repo>/audit.json` — 机器可读,每个架构职责定位到文件/符号/行号+代码证据,适合喂给 AI 继续追问;
- `agent-code-atlas-output/<repo>/report.html` — 交互式离线报告,双击即开:架构分层图、执行链路、状态模型、扩展点、二开配方、未知项;
- `agent-code-atlas-output/comparison-report.html` — 六方对比主入口:55 概念能力矩阵、9 个概念深比、26 条未确认问题;
- `agent-code-atlas-output/deepseek-harness/report.html` — DSH 单项目报告(独立审计):cordis waterfall 拦截体系、JSONL v3 存储契约、单调 guard 授权的完整解剖。

用法建议:选型前翻 Comparison 页的安全/持久化/循环三行;上手某框架前看它的 Runtime Flows 和 Development Guide;想验证文中任何一句话,grep 报告里的 file:line 去源码里对。

## 附录 A:选型十二问(三层清单)

**第一层:适配(装得下吗)——有一条不过直接淘汰**
1. **程序语言/技术栈**:要不要跨进程对接、养两套依赖?
2. **领域对口**:它带的手牌是为我的活设计的吗?
3. **维护主体**:坏了算框架的、厂商的、还是我的?闭源我控不了什么?

**第二层:能力(手牌够吗)**
4. **安全/沙箱默认值**:默认路径上有没有闸?
5. **审批/HITL**:能不能暂停等人?审批后能不能续跑?
6. **长期记忆**:跨会话记不记?自动沉淀、显式注册、还是没有?
7. **压缩/上下文管理**:窗口满了谁管?
8. **子代理/多 agent 原语**:有没有隔离派发,还是只能自己嵌套?
9. **模型接入**:翻译层谁维护?缓存语义翻不翻译(不翻=账单翻倍)?

**第三层:工程(养得起吗)**
10. **持久化与可恢复**:崩溃后从哪继续?消息可重放,还是执行状态可续跑?
11. **可调试性**:出错能静态定位,还是只能跑起来追?有没有完整回放?
12. **失控保护+成本可见**:turn 上限/预算保险丝默认开吗?token 记账和缓存命中透不透明?

## 附录 B:八家能力总表

✅=开箱即用 ⚠️=要配/有折损 ❌=没有,自己造

| | 语言栈 | 定位 | 谁维护 | 沙箱安全 | 审批 HITL | 长期记忆 | 压缩 | 子代理 | 模型接入 | 持久化/恢复 | 可调试性 | 失控保护 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Codex** | Rust(改难) | 编码 CLI | OpenAI·开源 | ✅✅ OS沙箱默认+审批双链 | ✅✅ 三级 fail-closed | ✅ 后台提取 | ✅ mid/post 双时机 | ✅ 子线程·审批关 | ⚠️ 钉 Responses,走厂商端点 | ✅ rollout JSONL 可重放 | ⚠️ 可回放,130 crate 难读 | ⚠️ 无轮数上限,靠语义+取消 |
| **Claude Code/SDK** | 内核闭源+SDK壳 | 编码 CLI | Anthropic·闭源 | ✅ 六模式(canUseTool) | ✅ 六模式+回调 | ⚠️ 文件约定(CLAUDE.md) | ✅ CLI 自动 | ✅ Task 工具·独立会话 | ⚠️ 绑 Claude,走兼容端点 | ✅ jsonl+SDK 镜像 | ❌ 黑盒,只见镜像 | ⚠️ --max-turns 可配 |
| **Pi** | TS | 极简内核·教学 | 开源 MIT·社区小 | ❌ 交容器 | ❌ 钩子自制 | ❌ 无 | ✅ 阈值触发 | ❌ 嵌套调用 | ✅ 按协议 42 模型 | ✅✅ JSONL 树·分支回滚 | ✅✅✅ 140 行全可读 | ❌ 无上限无预算 |
| **OpenAI Agents SDK** | Python | 通用库 | OpenAI·开源 | ⚠️ 逐工具 opt-in | ✅ 中断存档续跑 | ❌ 无提取(有 Session) | ❌ 无自动 | ✅ handoff+as_tool | ✅✅ litellm 一行接 | ✅ RunState 序列化 | ✅ tracing 全(_run_impl 难改) | ✅ max_turns 默认 10 |
| **LangGraph** | Python/TS | 图引擎 | LangChain·开源 | ❌ 引擎不管 | ✅✅ interrupt/resume 最强 | ⚠️ Store 原语自建 | ❌ 自建 | ✅ 子图/Send | ✅✅ 模型无关 | ✅✅ 快照+时间旅行 | ✅✅ 状态历史可查 | ✅ recursionLimit=25 |
| **deepagents** | Python | 预组装成品 | LangChain·开源 | ⚠️ 文件权限真,shell 直跑宿主无隔离 | ✅ 自动装配 HITL 中断 | ⚠️ MemoryMiddleware+Store 原语 | ⚠️ summarization 中间件 | ✅ 预装 | ✅ 同基座 600+ | ✅ 同基座快照 | ✅ 同基座 | ✅ 同基座 recursionLimit=25 |
| **DeepSeek Harness** | TS(Node) | 插件化 harness | DeepSeek·开源 | ✅✅ 双层授权+三档沙箱 fail-closed | ✅ ask+单调 guard | ⚠️ 无隐式,4 种显式替代 | ✅ 0.8×窗口 | ✅ 多后端外派(可派 Claude) | ✅ 插件·每请求路由 | ✅ 事件溯源 JSONL(默认不落盘要配) | ✅ 事件可回放,拦截点多难追 | ⚠️ 无上限 |
| **Hermes** | Python | 个人助理产品 | Nous·产品 | ⚠️ 审批门自认非隔离,默认裸跑 | ✅ 人审门 | ✅✅ 学习循环自动沉淀 | ✅ 每轮预检门 | ✅ delegate·心跳/转向 | ✅✅ 运行时热切换 | ✅✅ SQLite·先落库后执行 | ❌★ 反射状态机静态读不了 | ✅ 名义无限+预算兜底 |

**三行看懂**:竖读一列=一道题的全部业界答案;横读一行=一个项目的体检报告;**没有全绿的一行**——Codex 输在"改"、Pi 输在"安全手牌"、Hermes 输在"可调试"、OpenAI SDK 输在"上下文管理",选型就是把你的场景权重乘上去,看谁的 ❌ 落在你不 care 的列。

---

*审计边界:全程只读静态分析,未运行任何目标代码。DeepSeek Harness 审计于 2026-10-01、deepagents 审计于 2026-10-08(rev 6a3a12b),两者为独立单项目审计,未进入本轮六方对比矩阵。langchain 不在样本内(纯底座库,非 agent 框架)。闭源 CLI 按协议面黑盒处理。*
