# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⛔ 当前阶段与硬性约束（最高优先级）

- **当前阶段：Phase 0 初始化前。** 仓库为空（仅 `git init`，无任何提交）。
- **禁止擅自编写任何业务代码或生成脚手架**，直到用户明确确认 **Task 01**。
- 具体禁止事项（在 Task 01 确认前）：
  - 不创建源码文件（Python / TypeScript / SQL 等）
  - 不初始化 `package.json`、Next.js、FastAPI 项目、Prisma、Docker、docker-compose 等
  - 不安装依赖、不运行代码生成器
- 允许事项：读取/整理文档、回答问题、更新本文件、规划讨论。

## 项目概述

**AI Skill Benchmark 评测与推荐平台** —— 国内首个跨平台 AI 办公 Skill/Agent 的第三方评测、评分与推荐平台。收录所有可通过正常渠道取得的公开 Skill，通过全量静态检测和分级动态实测，为用户推荐适合其项目、平台、预算和安全要求的 Skill 及 Skill 组合（Bundle）。

首期覆盖平台：WorkBuddy（腾讯）、千问办公（阿里）、豆包工作（字节）；扩展来源：GitHub、Hugging Face、创作者公开提交。

## 需求基线文档

三份基线文档位于仓库内 `docs/` 目录（尚未 git 提交）：

- `docs/prd.md` — 产品需求规格说明书 v1.0（2026-08-26），需求基线
- `docs/tech-design.md` — 技术架构方案 统一版 V1.0
- `docs/business-plan.md` — 商业计划书 v1.0

**冲突裁决顺序：PRD > 商业计划书 > 技术方案。**

## 范围边界（来自 PRD 已确认决策，不得违反）

- 企业私有 Skill 完全排除：不获取、不测试、不展示（D-002）
- 不销售 Skill 文件、不提供下载，安装一律跳转原始来源（D-004/D-005）
- 不镜像三家平台市场（D-006）
- 不用下载量/Star/单次 LLM 打分冒充真实能力排名（D-007）
- 未实测不生成动态分数；静态失败不生成动态能力分（D-008）
- 推荐单位是项目 Skill Bundle（轻量/平衡/增强三档）（D-010）
- Skill、连接器/MCP、专家/工作伙伴分开建模，不混口径（D-011）
- 高风险操作（删除、支付、发送、发布、审批、生产写入）必须人工确认（D-012）
- Marketplace（付费交易与文件交付）、一键跨平台安装：**延期至 Phase 3，本期不设计、不预留接口**

## 技术栈（来自技术方案，实施时以 Task 确认为准）

五层架构：

| 层 | 职责 | 主要技术 |
| --- | --- | --- |
| L1 采集层 | 六类来源适配器、增量调度、六层去重 | Python + GitHub/HF API + Playwright（仅正常公开页面） |
| L2 数据层 | Canonical Skill Schema、Artifact 版本库、状态机 | PostgreSQL + S3 兼容对象存储 + SHA-256 |
| L3 执行层 | 静态扫描、中立沙箱、原生 Worker（Phase 2） | Docker 一次性容器 + Windows VM 快照 + 任务 DSL |
| L4 评分层 | 确定性验证优先、LLM 裁判池（补充）、八维聚合、证据等级 | pytest 式断言 + 四裁判池 + 金标集校准 |
| L5 应用层 | 前台搜索/详情/对比、推荐 Bundle 引擎、管理后台 | Next.js + FastAPI + Redis |

关键原则：确定性验证优先于 LLM 裁判；每次运行留痕（环境快照、输入输出、成本、日志）；评分必须带证据等级（A/B/C/D/U）和样本量。

## 目录约定（暂定，待 Task 01 确认后生效）

尚未创建任何源码目录（当前仅有 `docs/`）。实施时预期按五层架构组织（如 `collector/`、`schema/`、`analyzer/`、`sandbox/`、`scoring/`、`web/`、`api/`），具体结构在 Task 01 中确认，**不要提前创建**。

## 开发阶段

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| **Phase 0** | 验证与规范期（2~4 周）：来源 PoC、Canonical Schema、许可分级规则、30 个标准任务草案、静态检测规则集、沙箱原型、50 个 Skill 端到端试评 | **← 当前（尚未启动，等待 Task 01 确认）** |
| Phase 1 | 公开目录与中立评测 MVP（6~10 周）：五类来源、搜索/详情/对比、全量静态检测、中立动态测试、八维评分、三档 Bundle、基础后台。验收门：≥100 去重可运行 Skill 完成中立测试 | 未开始 |
| Phase 2 | 三家原生测试与企业内测（8~12 周）：Windows 原生 Worker、企业批准清单、回归与紧急停用。前置：协议与法务评估 | 未开始 |
| Phase 3 | 规模化与生态合作：官方 Feed、深链接安装、Marketplace（单独立项） | 未开始 |

里程碑映射（4 人 × 3 月）：M1 = Phase 0 全部交付；M2 = 采集/静态/沙箱上线；M3 = 评分/推荐/前台上线，达成 Phase 1 验收门。

## 工作方式约定

- 一切实施工作以用户确认的 Task 编号为准（Task 01 起），未确认不动手
- 文档间冲突时按 PRD > 商业计划书 > 技术方案裁决，并向用户指出冲突点
- 不把 `D:\新建文件夹` 下的任何内容作为本项目的一部分

## 已确认技术决策（Task 01 评审结果）

> 状态更新（覆盖上文过时表述）：首次 commit `6de3aac`（master）已包含 `docs/` 与本文件；Task 01（规划）已完成评审。当前仍为 Phase 0，业务代码在 Task 02 确认前不动。

- Python 工具链：uv（单一 workspace，lockfile 共享）
- 前端包管理：pnpm
- 数据库：PostgreSQL 16 + SQLAlchemy 2.0 + Alembic
- 对象存储：本地 MinIO（docker-compose），生产待定
- Redis：Phase 1 再引入，Phase 0 不使用
- 隐藏测试集：独立私有仓库，公共仓库 .gitignore 排除
- CI：GitHub Actions，推远端时再配置
- 范围：frontend/ 和 backend/ 目录在 Task 02 建骨架但不写业务代码
- 文档冲突裁决：PRD > 商业计划书 > 技术方案

## 准入判定规则（Task 05 评审确认）
- analyzer.has_fail 只是信号，不直接触发状态转移
- secrets FAIL → STATIC_BLOCKED（进 QUARANTINED）
- structure FAIL → WARN，允许继续到沙箱
- 其余 FAIL → NEED_REVIEW（人工复核）
- 三权利位全 NEED_INFO → 禁止进动态测试（D-008 合规红线）
- 以上映射由后续编排层（Task 06/07）实现，analyzer 层不负责
