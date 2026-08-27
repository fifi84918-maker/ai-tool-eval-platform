# Database Layer

PostgreSQL 16 + SQLAlchemy 2.0 + Alembic 数据持久化层。

## Quick Start

### 1. 启动 PostgreSQL（开发环境）

```bash
# 使用 Docker Compose 启动 PostgreSQL 16
docker-compose up -d postgres

# 检查容器状态
docker-compose ps
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，确保 DATABASE_URL 正确
# DATABASE_URL=postgresql+psycopg://skilleval:skilleval_dev_pass@localhost:5432/skilleval_db
```

### 3. 运行数据库迁移

```bash
# 查看迁移历史
alembic history

# 执行迁移（升级到最新版本）
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

### 4. 验证数据库

```bash
# 连接 PostgreSQL
psql postgresql://skilleval:skilleval_dev_pass@localhost:5432/skilleval_db

# 查看表结构
\dt
\d skills
\d artifact_references
```

## 项目结构

```
db/
├── __init__.py           # 数据库配置和 session 管理
└── models.py             # SQLAlchemy 模型（Skill, ArtifactReference）

alembic/
├── versions/
│   └── 001_initial_schema.py  # 初始迁移：skills + artifact_references
├── env.py                # Alembic 环境配置（从 .env 读取 DATABASE_URL）
├── script.py.mako        # 迁移脚本模板
└── README                # Alembic 使用说明

alembic.ini               # Alembic 配置文件
docker-compose.yml        # PostgreSQL 16 容器定义
```

## 模型说明

### Skill 模型

- 对应 PRD 中的 Skill 核心元数据
- **不存储 manifest 正文、脚本源码、二进制内容**（PRD D-005）
- 字段：skill_id（唯一）、canonical_name、source_kind、status、evidence_grade 等
- JSON 字段：declared_permissions、static_summary、admission_reasons、warnings

### ArtifactReference 模型

- **只存储对象存储指针**（bucket/key/sha256），不存储内容（PRD D-005）
- 用于引用 MinIO/S3 中的 artifact 文件
- 字段：skill_id、bucket、key、sha256、size_bytes、summary

## 测试

```bash
# 运行数据库模型测试（使用 SQLite in-memory）
pytest tests/test_db_models.py -v

# 运行所有测试
pytest tests/ -q
```

## 迁移工作流

### 创建新迁移

```bash
# 修改 db/models.py 后，自动生成迁移脚本
alembic revision --autogenerate -m "add new field to skills"

# 检查生成的迁移文件
cat alembic/versions/<revision>_add_new_field_to_skills.py

# 应用迁移
alembic upgrade head
```

### 手动创建迁移

```bash
# 创建空白迁移脚本
alembic revision -m "custom migration"

# 编辑 alembic/versions/<revision>_custom_migration.py
# 实现 upgrade() 和 downgrade() 函数
```

## 注意事项

1. **不提交 .env 文件**（已在 .gitignore 中）
2. **迁移必须幂等**：可重复执行，不产生副作用
3. **生产环境**：使用 RDS/云数据库，配置连接池、备份策略
4. **Phase 1**：仅基础 CRUD，复杂查询留 Phase 2
5. **集成测试**：当前用 SQLite in-memory，生产集成测试可用 testcontainers

## Phase 2 TODO

- [ ] MinIO 对象存储集成（evidence bucket）
- [ ] 复杂查询优化（全文搜索、分面过滤）
- [ ] 读写分离配置
- [ ] 连接池调优
- [ ] 数据库监控和慢查询分析
