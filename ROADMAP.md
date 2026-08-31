# AI Tool Evaluation Platform — Roadmap

## Phase 1 MVP（已完成 ✅）

### 阶段成果（7 个 commit，441 passed / 7 skipped）

| Commit  | 阶段  | 内容 |
|---------|-------|------|
| d95ab8e | V1B   | 前端增强 + SQLite 持久化 |
| c7700e7 | V1C   | 搜索过滤 + SQLite 结果缓存 |
| aa4ba02 | V1D   | 动态评分（subprocess 轻量版，opt-in） |
| 78ab830 | P0-1  | 静态检测 + 11 态 status |
| dff95bf | P0-2  | 八维评分 + evidence_level |
| a8ee01b | P1    | 兼容判定（Portable Core + Host Overlay） |
| 7c589b5 | P2    | 推荐动态权重 + 冲突检测 |

### 架构（L1–L5）

- **L1 采集**：GitHub 适配器 + 去重
- **L2 数据**：SQLite + 11 态状态机 + 搜索缓存
- **L3 执行**：StaticChecker + DynamicExecutor（subprocess，默认关闭）
- **L4 评分**：八维维度 + evidence_level A/B/C/D/U
- **L5 应用**：前端 + 推荐引擎 + 兼容判定 API

### 核心设计约束（不可退）

1. **确定性优先**：静态/规则/正则，不调 LLM
2. **无加载证据不得标 COMPATIBLE**（P1 硬约束，有专项测试）
3. **动态评分默认关闭**（`DYNAMIC_SCORING=enabled` 才启用）
4. **幂等补列**：所有新字段通过 `_ensure_columns` 懒初始化
5. **NULL 安全**：旧 DB / 旧 API 响应全部兼容

### 数据表字段（当前 skills 表）

```
status, entity_type, license, risk_flags, status_changed_at, canonical_name,
dynamic_score, dimensions_json, evidence_level, sample_size,
compat_status, compat_details_json
```

快照表：`skill_scores`, `skill_compat`

### API 清单

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/skills` | 技能列表（搜索 + 分页） |
| GET | `/api/v1/skills/{id}` | 技能详情（JSON-LD） |
| GET | `/api/v1/skills/{id}/scores` | 八维评分 + evidence_level |
| GET | `/api/v1/skills/{id}/compat` | 兼容判定（Portable Core + Host Overlay） |
| GET | `/api/v1/recommend/skills` | 兼容权重排序推荐 + 冲突检测 |
| POST | `/api/v1/recommend` | Bundle 推荐（项目画像） |

### 已知限制（诚实标注）

- Windows 不支持 Docker 原生测试（需 WSL2 / Linux）
- 八维中 `stability` / `cost_efficiency` / `platform_compat` 暂为 `null`（待 Phase 2 填充）
- 推荐 `context_boost = 0`（待用户画像接入）
- 重叠检测用 Jaccard，未用 embedding

---

## Phase 2 待办（按优先级）

### 🎯 P2-A 前端整合（当前进行中）

把 Phase 1 后端数据可视化：status badge / risk flags / 八维评分卡 / 兼容判定 / 推荐 rank + conflicts

### 🔴 P2-B 八维真实数据填充

| 维度 | 当前 | Phase 2 方案 |
|------|------|-------------|
| `stability` (15%) | null | repeat-run pass-rate |
| `cost_efficiency` (10%) | null | test_runs cost_info |
| `platform_compat` (10%) | null | platform_test_results |

### 🔴 P2-C 原生测试系统

Docker + DSL + Native Worker，需 WSL2 / Linux CI 环境

### 🟡 P2-D LLM 裁判

evidence A/B 第三层，作为静态+动态之外的补充验证

### 🟢 P2-E 推荐增强

- `context_boost`：用户画像接入
- Embedding 相似度替换 Jaccard
- 动态权重（数据驱动）

### ⏳ P2-F 企业治理

认证 / 申诉流程 / 审计日志

---

## 本地开发

```powershell
# 后端
cd C:\Users\EDY\ai-tool-eval-platform
uvicorn api.main:app --reload --port 8000

# 前端
cd web
pnpm dev    # http://localhost:3000
```

### 测试

```powershell
python -m pytest tests/ -q
# 期望：441 passed, 7 skipped, 0 failed
```

### Git 推送（SSH，HTTPS 443 被干扰）

```powershell
git remote -v
# 应为：git@github.com:fifi84918-maker/ai-tool-eval-platform.git
git push origin master
```

---

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-08-31 | V1D 由"完整动态评分"收敛为"subprocess 轻量版" | 确定性优先，避免 LLM 依赖 |
| 2026-08-31 | 推送方式由 HTTPS 切换为 SSH | 解决 Connection reset（443 端口干扰） |
| 2026-08-31 | Phase 1 MVP 闭环（L1-L5 骨架 + 前端 + 文档） | 先跑通全链路再垂直深化 |
| 2026-08-31 | 无加载证据不得标 COMPATIBLE | §6.3 硬约束，避免误导消费者 |
| 2026-08-31 | 幂等补列（`_ensure_columns`）而非 Alembic migration | 轻量，单机 SQLite 场景无需迁移框架 |
