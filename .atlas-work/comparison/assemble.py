# -*- coding: utf-8 -*-
"""组装 comparison.json:projects + source_audits + capability_matrix + 概念深比等。"""
import json, os, sys, re, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parts_concepts import CONCEPT_COMPARISONS
from parts_meta import FLOW_COMPARISONS, EXTENSION_COMPARISONS, ARCHITECTURAL_DIFFERENCES, COMMON_PATTERNS, TRADEOFFS

BASE = r"agent-code-atlas-output"
WORK = r".atlas-work\comparison"
REPOS = [
    ("codex", "codex", "Codex CLI (codex-rs)"),
    ("claude-code-sdk", "claude-agent-sdk-python", "Claude Agent SDK (Python)"),
    ("pi", "pi-mono", "Pi (pi-mono)"),
    ("openai-agents", "openai-agents-python", "OpenAI Agents SDK (Python)"),
    ("hermes", "hermes-agent", "Hermes Agent"),
    ("langgraphjs", "langgraphjs", "LangGraph.js"),
]
CONCEPT_NAMES = {
    "entry.sdk-api": "SDK API 入口", "entry.cli": "CLI 入口",
    "lifecycle.session": "会话", "lifecycle.agent": "Agent 实体", "lifecycle.run": "Run 执行实例",
    "lifecycle.cancel": "取消", "lifecycle.resume": "恢复",
    "orch.agent-loop": "Agent 主循环", "orch.turn-execution": "单轮执行", "orch.stop-condition": "停止条件",
    "orch.retry": "重试", "orch.subagent": "子智能体", "orch.human-approval": "人工审批", "orch.orchestrator": "编排器",
    "state.message-history": "消息历史", "state.context-builder": "上下文组装", "state.system-prompt": "系统提示词",
    "state.compaction": "上下文压缩", "state.truncation": "历史截断", "state.persistence": "持久化",
    "state.checkpoint": "检查点", "state.memory": "跨会话记忆",
    "model.client": "模型客户端", "model.provider-abstraction": "供应商抽象", "model.streaming": "模型流式",
    "model.message-mapping": "消息映射", "model.tool-schema-conversion": "工具 schema 转换",
    "model.usage-accounting": "用量记账", "model.retry": "模型重试",
    "tool.registry": "工具注册表", "tool.dispatch": "工具分派", "tool.declaration": "工具声明",
    "tool.param-validation": "参数校验", "tool.result-serialization": "结果序列化", "tool.builtin": "内置工具", "tool.mcp": "MCP 集成",
    "exec.executor": "执行器", "exec.sandbox": "沙箱机制", "exec.process-runner": "进程运行器",
    "exec.output-truncation": "输出截断", "exec.timeout": "超时",
    "perm.authorization": "权限判定", "perm.user-confirmation": "用户确认", "perm.allow-deny-list": "允许/拒绝清单",
    "perm.path-restriction": "路径限制",
    "obs.event-model": "事件模型", "obs.streaming-events": "流式事件", "obs.event-bus": "事件总线", "obs.callbacks": "回调",
    "ext.tool-provider": "工具提供者扩展点", "ext.provider-adapter": "供应商适配扩展点", "ext.plugin-system": "插件体系",
    "ext.hooks": "钩子扩展", "ext.mcp-as-extension": "MCP 扩展通道", "ext.protocol-adapter": "协议适配",
}

def clean(s, n=None):
    s = re.sub(r"\s+", " ", s).strip()
    if n and len(s) > n:
        s = s[: n - 1].rstrip("、;,;") + "…"
    return s

audits, projects = {}, []
extract = json.load(open(os.path.join(WORK, "extract.json"), encoding="utf-8"))
for i, (pid, d, name) in enumerate(REPOS):
    a = json.load(open(os.path.join(BASE, d, "audit.json"), encoding="utf-8"))
    audits[pid] = a
    projects.append({"id": pid, "name": name, "root": a["project"]["root"],
                     "revision": a["project"].get("revision"), "audit_index": i})

# ---- capability_matrix ----
all_concepts = []
seen = set()
for c in CONCEPT_NAMES:
    all_concepts.append(c); seen.add(c)
for info in extract.values():
    for c in info["concepts"]:
        if c not in seen:
            all_concepts.append(c); seen.add(c)

matrix = []
for c in all_concepts:
    cells = []
    for pid, _, _ in REPOS:
        ce = extract[pid]["concepts"].get(c)
        if not ce or ce["status"] == "MISSING_NODE":
            cells.append({"project_id": pid, "status": "unknown", "summary": "audit 中未找到对应节点"})
            continue
        n0 = ce["nodes"][0]
        refs = [f"node:{n0['id']}"] + [f"file:{fid}" for fid in []]
        cells.append({"project_id": pid, "status": n0["status"],
                      "summary": clean(n0["summary"], 180), "refs": refs})
    matrix.append({"concept_id": c, "concept_name": CONCEPT_NAMES.get(c, c), "cells": cells})

# ---- concept_comparisons: 解析 (pid, canonical) → refs ----
node_index = {}   # (pid, canonical) -> [node dicts]
for pid, a in audits.items():
    fids = {f["id"]: f for f in a.get("files", [])}
    for n in a.get("architecture_nodes", []):
        node_index.setdefault((pid, n["canonical_id"]), []).append((n, fids))

def resolve_concept_refs(pid, canonical):
    out = []
    for n, fids in node_index.get((pid, canonical), []):
        out.append(f"node:{n['id']}")
        for fid in n.get("file_ids", [])[:2]:
            if fid in fids:
                out.append(f"file:{fid}")
        break
    return out

concept_comparisons = []
for cc in CONCEPT_COMPARISONS:
    pp = []
    for p in cc["per_project"]:
        q = dict(p)
        q["refs"] = resolve_concept_refs(*p["refs"][0]) if p.get("refs") else []
        pp.append(q)
    concept_comparisons.append({"concept_id": cc["concept_id"], "concept_name": cc["concept_name"],
                                "common_pattern": cc["common_pattern"], "difference_summary": cc["difference_summary"],
                                "per_project": pp})

# ---- flow_comparisons: 处理占位 ref ----
PLACEHOLDER = {"node:ROLLING": ("codex", "state.checkpoint"), "node:RUNSTATE": ("openai-agents", "state.checkpoint")}
flow_comparisons = []
for fc in FLOW_COMPARISONS:
    pp = []
    for p in fc["per_project"]:
        q = dict(p)
        refs = []
        for r in q.get("refs", []):
            if r in PLACEHOLDER:
                refs.extend(resolve_concept_refs(*PLACEHOLDER[r]))
            else:
                refs.append(r)
        q["refs"] = refs
        pp.append(q)
    flow_comparisons.append({"topic": fc["topic"], "summary": fc["summary"], "per_project": pp})

ext_comparisons = []
for ec in EXTENSION_COMPARISONS:
    ext_comparisons.append({"topic": ec["topic"], "summary": ec["summary"], "per_project": [dict(p) for p in ec["per_project"]]})

# ---- unknowns 汇总 ----
unknowns, uid = [], 0
for pid, a in audits.items():
    for u in a.get("unknowns", []):
        uid += 1
        unknowns.append({"id": f"un-cmp-{uid:02d}", "project_id": pid, "question": u["question"],
                         "why_unknown": u.get("why_unknown", ""), "attempted_checks": u.get("attempted_checks", []),
                         "likely_locations": u.get("likely_locations", []), "impact": u.get("impact", ""),
                         "recommended_verification": u.get("recommended_verification", "")})

comparison = {
    "schema_version": "1.0",
    "report_kind": "comparison",
    "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "analyzer_version": "agent-code-atlas/1.0",
    "projects": projects,
    "source_audits": [audits[pid] for pid, _, _ in REPOS],
    "capability_matrix": matrix,
    "concept_comparisons": concept_comparisons,
    "flow_comparisons": flow_comparisons,
    "extension_comparisons": ext_comparisons,
    "architectural_differences": ARCHITECTURAL_DIFFERENCES,
    "common_patterns": COMMON_PATTERNS,
    "tradeoffs": TRADEOFFS,
    "unknowns": unknowns,
}

os.makedirs(BASE, exist_ok=True)
outp = os.path.join(BASE, "comparison.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(comparison, f, ensure_ascii=False)
print("written", outp, os.path.getsize(outp), "bytes")
print("matrix rows:", len(matrix), "concepts:", len(concept_comparisons), "flows:", len(flow_comparisons),
      "ext:", len(ext_comparisons), "diffs:", len(ARCHITECTURAL_DIFFERENCES), "unknowns:", len(unknowns))
