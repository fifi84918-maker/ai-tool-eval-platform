# AI Skill Eval Platform

**跨平台 AI 办公 Skill/Agent 的第三方评测、评分与推荐平台**

收录公开 AI Skill，通过静态检测和动态实测，为用户推荐适合的工具。支持 GitHub URL 一键评估，自动计算质量评分（A/B/C/D/U）。

---

## 🚀 快速开始（Docker 一键部署）

### 前置要求
- [Docker](https://www.docker.com/get-started) 和 Docker Compose
- Git

### 启动步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/fifi84918-maker/ai-tool-eval-platform.git
   cd ai-tool-eval-platform
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   ```
   可选：编辑 `.env` 修改数据库密码（推荐修改 `POSTGRES_PASSWORD`）

3. **启动所有服务**
   ```bash
   docker compose up -d --build
   ```
   - 首次构建需要 5-10 分钟（下载镜像 + 安装依赖）
   - 包含三个服务：PostgreSQL 数据库、后端 API、前端 Web

4. **等待服务就绪**
   ```bash
   docker compose logs -f
   ```
   看到 `Application startup complete` 后按 `Ctrl+C` 退出日志

5. **访问应用**
   - **前端**：http://localhost:3000
   - **API 文档**：http://localhost:8000/docs
   - **API 根路径**：http://localhost:8000

6. **（可选）导入示例数据**
   ```bash
   docker compose exec backend python scripts/seed_with_scores.py
   ```

### 停止服务
```bash
docker compose down
```

保留数据（下次启动时数据仍在）：
```bash
docker compose down  # 只停止容器
```

完全清理（删除数据库和卷）：
```bash
docker compose down -v
```

---

## 💻 本地开发（不使用 Docker）

### 前置要求
- Python 3.12+
- Node.js 20+
- PostgreSQL 16（或使用 SQLite）
- [uv](https://github.com/astral-sh/uv)（Python 包管理器）
- [pnpm](https://pnpm.io/)（Node 包管理器）

### 后端开发

1. **安装依赖**
   ```bash
   uv sync
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 配置数据库连接
   ```
   本地开发可使用 SQLite：
   ```bash
   export DATABASE_URL="sqlite:///./skillbench.db"
   export PYTHONPATH="$(pwd)"
   ```

3. **启动 API 服务器**
   ```bash
   uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   访问 http://localhost:8000/docs 查看 API 文档

4. **运行测试**
   ```bash
   uv run pytest tests/ -v
   ```

5. **导入示例数据**
   ```bash
   uv run python scripts/seed_with_scores.py
   ```

### 前端开发

1. **安装依赖**
   ```bash
   cd web
   pnpm install
   ```

2. **启动开发服务器**
   ```bash
   pnpm dev
   ```
   访问 http://localhost:3001

3. **构建生产版本**
   ```bash
   pnpm build
   pnpm start
   ```

4. **Lint 检查**
   ```bash
   pnpm lint
   ```

---

## 🔍 评估一个 GitHub 仓库

1. 访问 **http://localhost:3000/eval**
2. 粘贴任意 GitHub 仓库 URL（例如：`https://github.com/torvalds/linux`）
3. 点击 **Evaluate** 按钮
4. 等待 10-30 秒（克隆 + 分析）
5. 查看评分结果：
   - 总分（0-100）
   - 等级（A/B/C/D/U）
   - 四维度明细（Accuracy / Reliability / Security / Performance）

---

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| **后端** | FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 |
| **前端** | Next.js 14 + Tailwind CSS + TypeScript |
| **评分引擎** | Python（多维度加权计算） |
| **部署** | Docker + Docker Compose |
| **测试** | pytest（170+ 测试用例） |

---

## 📁 项目结构

```
ai-tool-eval-platform/
├── api/                    # FastAPI 路由与 schemas
│   ├── main.py            # 应用入口
│   ├── routers/           # API 端点
│   │   ├── skills.py      # /api/v1/skills
│   │   └── eval.py        # /api/v1/eval（评估 GitHub URL）
│   └── schemas.py         # Pydantic 模型
├── db/                     # 数据库层
│   ├── models.py          # SQLAlchemy ORM 模型
│   ├── repository.py      # 数据访问层
│   └── migration_add_score.py  # 迁移脚本
├── scoring/                # 评分引擎
│   ├── engine.py          # score_skill() 核心逻辑
│   └── grades.py          # 等级阈值（A≥90, B≥75, C≥60, D≥40, U<40）
├── scripts/                # 工具脚本
│   ├── seed_with_scores.py    # 导入示例数据（含评分）
│   └── run_api.py         # 本地启动 API
├── tests/                  # 测试套件
│   ├── test_scoring.py    # 评分引擎测试（17 个）
│   ├── test_scoring_persistence.py  # 持久化测试（6 个）
│   └── test_eval_url.py   # URL 评估测试（6 个）
├── web/                    # Next.js 前端
│   ├── src/
│   │   ├── app/           # 页面路由
│   │   │   ├── page.tsx   # 首页（搜索 + 列表）
│   │   │   ├── eval/page.tsx      # 评估页面
│   │   │   └── skills/[skill_id]/page.tsx  # 详情页
│   │   └── components/skill/
│   │       ├── GradeBadge.tsx     # 等级徽章
│   │       └── ScoreBar.tsx       # 评分进度条
│   ├── Dockerfile         # 前端容器构建
│   └── package.json       # Node 依赖
├── Dockerfile             # 后端容器构建
├── docker-compose.yml     # 三服务编排（postgres + backend + frontend）
├── pyproject.toml         # Python 依赖
└── README.md              # 本文件
```

---

## 📊 评分维度

评分引擎基于四个维度计算综合得分：

| 维度 | 权重 | 检测项 |
|------|------|--------|
| **Accuracy** | 30% | 文档完整性、测试覆盖、CI 配置 |
| **Reliability** | 30% | 依赖管理、锁文件、.gitignore |
| **Security** | 20% | 凭证扫描、敏感文件、安全策略 |
| **Performance** | 20% | 容器化、缓存配置、依赖数量 |

**等级划分：**
- **A**：≥90 分（优秀）
- **B**：≥75 分（良好）
- **C**：≥60 分（及格）
- **D**：≥40 分（较差）
- **U**：<40 分（不合格）

---

## 🧪 测试

### 运行所有测试
```bash
uv run pytest tests/ -v
```

### 运行特定测试
```bash
uv run pytest tests/test_scoring.py -v
uv run pytest tests/test_eval_url.py -v
```

### 测试覆盖
- **170+ 测试用例**
- **评分引擎**：17 个单元测试
- **持久化**：6 个集成测试
- **URL 评估**：6 个端到端测试

---

## 🐛 故障排查

### Docker 相关问题

**端口冲突（8000 或 3000 已被占用）**
```bash
# 检查占用进程
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 修改 docker-compose.yml 中的端口映射
ports:
  - "8001:8000"  # 后端
  - "3001:3000"  # 前端
```

**容器启动失败**
```bash
# 查看日志
docker compose logs backend
docker compose logs frontend

# 重新构建
docker compose up -d --build --force-recreate
```

**数据库连接失败**
```bash
# 确认 PostgreSQL 健康检查通过
docker compose ps

# 手动测试连接
docker compose exec postgres psql -U skillbench -d skillbench
```

### 本地开发问题

**模块导入错误**
```bash
# 确保设置 PYTHONPATH
export PYTHONPATH="$(pwd)"
```

**前端 API 调用失败**
```bash
# 检查后端是否运行
curl http://localhost:8000

# 检查环境变量
echo $NEXT_PUBLIC_API_BASE_URL
```

---

## 📝 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

开发流程：
1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/amazing-feature`）
3. 提交改动（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 提交 Pull Request

---

## 📧 联系方式

- **项目地址**：https://github.com/fifi84918-maker/ai-tool-eval-platform
- **Issues**：https://github.com/fifi84918-maker/ai-tool-eval-platform/issues

---

**当前状态：Phase 2 完成 — 170+ 测试用例通过，Docker 一键部署，前后端完整集成**
