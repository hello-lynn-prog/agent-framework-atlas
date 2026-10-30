# SDK 代码级对比图谱（visuals）

> 生成于 2026-09-30 ｜ 依据：`../notes/sdk-*.md` ×10 源码级拆解笔记 ｜ 证据均带 file:line，可回溯到 `../harness-research/` 源码

## 两套图谱

| | 文件 | 视角 | 适合 |
| --- | --- | --- | --- |
| 机制图谱 | [sdk-对比图谱.html](sdk-对比图谱.html)（png/ ×8） | 架构视角：族谱/矩阵/模块对比 | 快速建立全景、查"谁有什么" |
| **代码对比** | [sdk-代码对比.html](sdk-代码对比.html)（png-code/ ×4） | **源码视角：7 家主循环真实代码逐行对比** | 看清"循环到底怎么写的"、共性高亮 |

代码对比四页导航：[code-1](png-code/code-1.png) 母版六步 + 10 家实现坐标 ｜ [code-2](png-code/code-2.png) 真码·OpenAI/Smolagents/Pi/dsh ｜ [code-3](png-code/code-3.png) 真码·Hermes/CASDK/Codex ｜ [code-4](png-code/code-4.png) 共性收束 + 事件日志真容。

**读法**：琥珀色高亮行 = 所有家都在实现的"母版六步"（①组装上下文 ②LLM采样 ③分支 ④执行工具 ⑤落历史 ⑥终止）——把七家高亮行连起来读是同一份代码；没高亮的行就是各家的差异器官。

## 机制图谱八页内容导航

| 图 | 文件 | 一句话 | 回答的问题 |
| --- | --- | --- | --- |
| 01 | [slide-1.png](png/slide-1.png) | 范式族谱 + 控制权光谱 | 这十家各是什么流派？循环归谁管？ |
| 02 | [slide-2.png](png/slide-2.png) | 六大共性 + 循环骨架图 | 拆掉外壳后，大家共有的骨架是什么？ |
| 03 | [slide-3.png](png/slide-3.png) | 八种主循环写法（带代码坐标） | 同一个循环，代码层有多少种实现？ |
| 04 | [slide-4.png](png/slide-4.png) | 多 Agent 三路线（换手/借用/隔离派发） | 子代理这件事有几种做法？产品系站哪队？ |
| 05 | [slide-5.png](png/slide-5.png) | 10 家 × 10 项特征矩阵 | 想快速查“谁有什么、谁没有什么” |
| 06 | [slide-6.png](png/slide-6.png) | 持久化四形态 + 压缩五时机 | 断点/分叉/压缩，代码层是怎么赌的？ |
| 07 | [slide-7.png](png/slide-7.png) | 安全 · 记忆 · 网关三模块 | 三大高频模块各家答案对比 |
| 08 | [slide-8.png](png/slide-8.png) | 命名对照表 + 刻意不做清单 + 抄作业清单 | 跨家读文档先对暗号；边界即设计决策 |

## 核心结论 30 秒版

1. **共性**：骨架同一个（while + LLM→工具→观察）；产品系无 turn 上限、清一色隔离派发、持久化收敛到 append-only 日志、压缩是标配、为 prompt cache 费尽心思。
2. **差异主轴**：控制权光谱——LangGraph 裸核（全可编程）→ dsh（可拦可换）→ Pi（仅回调）→ Hermes/Codex（编译进核）→ CASDK（黑盒挂钩子）。
3. **最值得抄的 4 个设计**：dsh 真前缀压缩（KV cache）、Codex 审批+OS 双链、Hermes fork 影子代理自学习、Pi 会话树零复制分叉。

## 重新生成

- 改了 `sdk-对比图谱.html` 后执行：`python _build_png.py`
- 改了 `sdk-代码对比.html` 后执行：`python _build_code_png.py`（自动拆页 + Edge 无头截图 + 按内容底边裁切）
