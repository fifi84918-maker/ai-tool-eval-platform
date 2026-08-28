# AI Tool Eval Platform — Project Snapshot

## 当前状态（2026-08-27）

- **Phase 1**：✅ Task 09–16 全部完成并 push
- **Task A**（体验补齐）：✅ 本地提交 7cc779c，待 push
- **Task 17**（评分引擎）：✅ 本地提交 caf3e9a，待 push
- **Task 18**（评分落库+API）：✅ 本地提交 16b4ecc，待 push
- **Task 19**（前端评分展示）：✅ 本地提交 119c837，待 push
- **本地领先远程 4 个 commit**，网络恢复后执行 `git push` 即可同步
- **测试基线**：164 passed, 2 skipped, 无回退

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite（本地）/ PostgreSQL（生产） |
| 前端 | Next.js 14 + Tailwind CSS + pnpm v11 |
| 评分引擎 | scoring/engine.py — 纯计算模块，多维度加权 |
| MCP Server | 4 个工具（skill_search / skill_detail / eval_status / list_artifacts） |
| 测试 | pytest，158+6=164 |

## 项目结构

```
ai-tool-eval-platform/
├── api/                              # FastAPI 路由 + schemas
│   ├── main.py                       # FastAPI app + CORS
│   ├── routers/skills.py             # /api/v1/skills 端点
│   └── schemas.py                    # Pydantic 模型（SkillSummaryOut 含 score_total/grade）
├── db/                               # 数据库层
│   ├── models.py                     # Skill ORM（含 score_total Float, grade String(2)）
│   ├── repository.py                 # SkillRepository（_to_dict_scrubbed 含评分字段）
│   ├── session.py                    # get_db 依赖
│   └── migration_add_score.py        # 幂等迁移脚本
├── scoring/                          # 评分引擎（Task 17）
│   ├── __init__.py                   # 导出 score_skill, GRADE_THRESHOLDS, Grade
│   ├── engine.py                     # score_skill(metrics, weights) → {total, grade, breakdown}
│   └── grades.py                     # Grade 枚举 + GRADE_THRESHOLDS + get_grade()
├── scripts/
│   ├── seed_samples.py               # 基础种子（5 个样本）
│   ├── seed_with_scores.py           # 带评分的种子（调用 score_skill → 写 DB）
│   └── run_api.py                    # 启动 FastAPI
├── tests/
│   ├── test_scoring.py               # 17 个评分引擎测试
│   └── test_scoring_persistence.py   # 6 个持久化测试
├── web/                              # Next.js 前端
│   └── src/
│       ├── components/skill/
│       │   ├── GradeBadge.tsx        # 彩色等级徽章
│       │   └── ScoreBar.tsx          # 动画进度条
│       └── app/
│           ├── page.tsx              # 列表页（含徽章+进度条）
│           └── skills/[skill_id]/page.tsx  # 详情页
├── pyproject.toml                    # Python 依赖（sqlalchemy, fastapi, uvicorn, mcp）
└── skillbench.db                     # 本地 SQLite（已在 .gitignore）
```

## 评分引擎 API

**Phase 1 静态评估：四维评分**

当前实现基于静态代码扫描的 4 个维度：

1. **Accuracy**（准确性，30%）：文档质量、测试覆盖
2. **Reliability**（可靠性，30%）：依赖管理、代码规范
3. **Security**（安全性，20%）：密钥扫描、安全策略
4. **Performance**（性能，20%）：容器化、异步模式

```python
from scoring import score_skill

result = score_skill(
    metrics={"accuracy": 90.0, "reliability": 85.0, "security": 80.0, "performance": 88.0},
    weights={"accuracy": 0.3, "reliability": 0.3, "security": 0.2, "performance": 0.2}
)
# → {"total": 86.1, "grade": "B", "breakdown": {"accuracy": 27.0, ...}}
```

**等级阈值：** A(≥90) / B(≥75) / C(≥60) / D(≥40) / U(<40)

**注：** PRD 中的"八维评分"（task_effect/stability/trigger_quality 等）是未来 Phase 2 动态运行时评估的目标，需要沙箱环境支持。当前 Phase 1 专注于静态代码质量的四维评分。

## 严格约束（所有 Task 必须遵守）

- ❌ 不修改 core/analyzer/collector/sandbox/orchestrator/compliance 内部
- ❌ 不改 scoring/ 引擎逻辑（只复用）
- ❌ 不引入新依赖（除非明确授权）
- ✅ 现有 164 个测试不能回退
- ✅ API 路由行为向后兼容（新字段 optional）

## 本地开发命令

```powershell
# 后端
cd C:\Users\EDY\ai-tool-eval-platform
$env:DATABASE_URL = "sqlite:///./skillbench.db"
$env:PYTHONPATH = "C:\Users\EDY\ai-tool-eval-platform"
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000

# 种子
uv run python scripts/seed_with_scores.py

# 测试
uv run pytest tests/ -q

# 前端
cd web && pnpm dev
```

## 下一步（MVP 冲刺）

| Task | 内容 |
|------|------|
| Task 20 | 用户粘贴 GitHub URL → clone → 提取指标 → 评分 → 返回 JSON |
| Task 21 | 前端 "Evaluate New Repo" 页面 → 调用 Task 20 API → 展示结果 |
| Task 22 | Docker Compose 一键起全栈 + README 部署说明 |

