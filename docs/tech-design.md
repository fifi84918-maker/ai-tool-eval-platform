# AI Skill Benchmark 评测与推荐平台

> 技术架构方案 · 统一版 V1.0

> 文档体系：04/07 · 实现层

> 基线依据：产品需求规格说明书 PRD v1.0（2026-08-26）

> 冲突裁决顺序：PRD > 商业计划书 > 技术方案

> 编制日期：2026年8月26日

# 修订说明（相对纯技术方案 V1.0）

| 修订项 | 原表述 | 统一版表述（按 PRD 裁决） |
| --- | --- | --- |
| Skill 主表 | 无收录状态字段 | 增加 status 字段，取值为 PRD 11 种收录状态 |
| 评分 API | 仅返回六维分数 | 返回 PRD 八维分数 + evidence_level + sample_size + 环境快照 |
| 判分流水线 | LLM 裁判为主 | 确定性验证优先，LLM 只作补充（PRD 15.1） |
| 兼容判断 | 单一兼容性检测 | Portable Core + Host Overlay 双路判断，输出 7 种兼容状态 |
| 推荐输出 | Skill 组合 / 工作流方案 | 统一为 Bundle（版本、依赖、权限、验收、回退齐备） |
| Marketplace/一键安装 | 列为远期模块 | 明确标注「延期至 Phase 3」，本方案不设计不预留接口 |
| 分期 | 4人×3月里程碑 | 映射到 Phase 0 / Phase 1（Phase 2-3 见路线图文档） |

# 一、AI-First 实现原则

1. 能用 AI 生成的代码不手写：脚手架、CRUD、解析器、测试用例均由 AI 辅助生成，人负责审查与集成。

1. 能用 AI 执行的流程不雇人：静态检测规则解释、任务脚本 DSL 编译、报告初稿均由 AI 完成，人做抽检。

1. 确定性优先：凡可用断言、diff、schema 校验、文件哈希验证的判分，一律不用 LLM；LLM 裁判仅用于风格与复杂产物辅助评审（PRD 15.1 第 7 条）。

1. 证据留痕：每次运行保存环境快照、输入、输出、成本与日志，保证可复现（对应证据等级 A/B 的"环境记录完整"要求）。

工作量测算：传统开发约 215 人天 → AI 优先约 81 人天（压缩 62%）；4 人 × 3 个月覆盖 Phase 0 + Phase 1。

# 二、五层系统架构

| 层 | 职责 | 关键组件 | 主要技术 |
| --- | --- | --- | --- |
| L1 采集层 | 五类来源发现与获取 | 来源适配器×6、增量调度、去重引擎（六层） | Python + GitHub/HF API + Playwright（仅正常公开页面） |
| L2 数据层 | 统一建模与状态机 | Canonical Skill Schema、Artifact 版本库、状态机引擎 | PostgreSQL + S3兼容对象存储 + SHA-256 |
| L3 执行层 | 静态检测与动态测试 | 静态扫描器、中立沙箱、原生Worker（Phase 2）、测试员Agent | Docker一次性容器 + Windows VM快照 + DSL |
| L4 评分层 | 判分、聚合与证据管理 | 确定性验证器、LLM裁判池、八维聚合器、证据等级判定器 | pytest式断言 + 四裁判池 + 金标集校准 |
| L5 应用层 | 前台、推荐与后台 | 搜索/详情/对比、项目画像、Bundle引擎、管理后台 | Next.js + FastAPI + 推荐服务 |

# 三、数据模型（核心表）

## 3.1 Skill 主表（skills）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| skill_id | UUID PK | 平台内唯一标识 |
| canonical_name | TEXT | 归一化名称 |
| status | ENUM | PRD 11 种收录状态：DISCOVERED / METADATA_ONLY / ACQUIRED / STATIC_REVIEWED / QUARANTINED / RUNNABLE / NEUTRAL_TESTED / NATIVE_TESTED / VERIFIED / STALE / REMOVED（有且只有一个当前主状态） |
| category / task_tags | TEXT[] | 任务类别标签（调研/文档/表格/演示/网页…） |
| entity_type | ENUM | SKILL / CONNECTOR_MCP / EXPERT —— 三者分开建模不混口径（D-011） |
| license | TEXT | SPDX 标识或 UNKNOWN（不明确须标记） |
| risk_flags | JSONB | 静态检测命中的安全/许可标记 |
| created_at / status_changed_at | TIMESTAMPTZ | 状态流转审计 |

## 3.2 其余主表

| 表 | 关键字段 | 要点 |
| --- | --- | --- |
| sources（来源） | source_id, skill_id, origin_url, author, discovered_at, is_alive | 一个 Skill 保留全部来源关系；出现次数与独立内容数分开统计 |
| artifacts（版本） | artifact_id, skill_id, sha256, dir_hash, version, acquired_via | 内容变化生成新 Artifact Version；完全重复共享测试结果 |
| test_runs（运行） | run_id, artifact_id, task_id, host, model, passed, cost_tokens, duration, env_snapshot, log_uri | 每次运行完整留痕；含无 Skill 基线运行 |
| scores（评分） | score_id, artifact_id, 八维分值, composite, evidence_level, sample_size, valid_until | 证据等级与样本量为必填；环境过期置 STALE |
| compat（兼容） | artifact_id, target_host, portable_core_result, host_overlay_result, compat_status | 7 种兼容状态；须有加载或冒烟证据才可标 Compatible |
| bundles（组合） | bundle_id, project_profile_id, tier(轻量/平衡/增强), items(职责/依赖/权限/限制/替代项/回退) | 推荐单位是 Bundle（D-010） |

# 四、采集与静态检测流水线

## 4.1 来源适配器

| 来源 | 接入方式 | 边界约束 |
| --- | --- | --- |
| WorkBuddy 公开市场 | 官方页面/正常客户端流程/经确认的公开包 | 不镜像市场（D-006） |
| 千问办公公开扩展 | 官方页面、正常客户端、本地已安装目录 | 无批量接口时人工补录并留操作记录 |
| 豆包工作公开 Skill | 官方页面和正常客户端 | 发布初期先做格式与路径 PoC |
| GitHub | API + 代码搜索（SKILL.md 及已知结构） | 遵循 API 限流与许可证元数据 |
| Hugging Face | Hub API、仓库卡、许可证元数据 | 同上 |
| 创作者提交 | 网页表单或仓库链接 | 入口拒收企业私有 Skill（D-002） |

收录五条件硬校验：普通用户可见或作者明确公开；可正常取得；不绕过验证码/权限/付费墙/限流/技术保护；非泄露或未授权备份；来源作者可追溯。命中排除来源（企业空间、借用账号、网盘泄露包、逆向导出、已删除内容缓存）直接拒收。

## 4.2 静态检测（全量）

- 覆盖：所有能取得 Artifact 的公开 Skill（D-008）；仅元数据候选只做来源核验并置 METADATA_ONLY。

- 维度：结构规范、许可证识别、高危命令扫描、凭证外传、隐藏网络请求、越权行为、依赖清单、文档完整度。

- 产出：风险标记写入 risk_flags；命中安全或许可阻断 → status 置 QUARANTINED；通过 → STATIC_REVIEWED。

- 验收（PRD 29.2）：90% 以上可取得 Artifact 在规定时间内完成静态检测；静态失败不生成动态能力分。

# 五、动态测试系统

## 5.1 准入与分级（D-009）

许可证、来源、安全、依赖和可运行性全部满足 → status 置 RUNNABLE，进入执行环境。测试层级 L0-L5：L0 加载冒烟 → L1 触发测试 → L2 单任务执行 → L3 多任务带基线 → L4 稳定性重复 → L5 组合（Bundle）测试。

## 5.2 双执行器架构

- 中立沙箱（Phase 0-1 主路径）：Docker 一次性容器，统一模型与工具配置，无生产凭证、网络白名单、环境间无文件/密钥/会话串扰；测出 Skill 本体能力。

- 原生 Worker（Phase 2）：Windows VM 快照 + 平台正常客户端（WorkBuddy / 千问办公 / 豆包工作），UIA + pyautogui + 多模态视觉自愈选择器；测出平台端到端表现，结果标记为「平台端到端」，不把差异全部归因于 Skill（PRD 16.3）。

- 任务步骤 DSL：人写任务意图，AI 编译为可执行脚本；测试员 Agent 负责编排、重试与异常上报。

## 5.3 基线与重复

每个任务先跑无 Skill 基线；Uplift = 使用 Skill 通过率 − 基线通过率。重复次数按证据等级目标配置：冲 A 级每任务 ≥5 次、≥3 个任务；B 级每任务 ≥3 次、≥2 个任务。一次运行不产生"已验证"标签。

# 六、判分与评分服务

## 6.1 三层判分流水线（确定性优先）

1. 第一层 确定性验证（主）：文件存在性、schema 校验、断言、diff、哈希、可执行性检查——凡可确定性验证的结论优先采用。

1. 第二层 规则化评估：格式合规、字数/结构约束、性能与成本阈值。

1. 第三层 LLM 裁判（补充，仅限风格与复杂产物）：四裁判池（GPT/Claude/千问/DeepSeek）抽三、同厂回避、来源匿名盲评、位置去偏、取中位；金标集校准门禁（与人工全评相关系数 ≥0.85 才准上线）；裁判 Prompt 版本化管理。

## 6.2 评分 API（对外契约）

GET /api/v1/skills/{skill_id}/scores 响应示例字段：

| 字段 | 说明 |
| --- | --- |
| dimensions | 八维分值：task_effect(35%) / stability(15%) / trigger_quality(10%) / permission_privacy(10%) / cost_efficiency(10%) / platform_compat(10%) / maintainability(5%) / doc_explainability(5%) |
| composite | 默认权重综合分（仅默认场景；推荐时按项目目标动态调权） |
| evidence_level | A / B / C / D / U —— 必返字段；D 级不返回动态效果结论 |
| sample_size | 样本量（任务数 × 重复次数）—— 必返字段 |
| uplift | 相对无 Skill 基线的增益 |
| env | 宿主、模型、客户端版本、测试日期（PRD 15.1：平台/模型/版本/时间必须可见） |
| status / valid_until | 收录状态与有效期；过期自动置 STALE 并触发回归 |

## 6.3 兼容判定服务

双路判断：① Portable Core 抽取（name/description/主体说明/scripts/references/assets/输入输出约定/依赖权限声明）→ 目标宿主加载或冒烟测试；② Host Overlay 分析（目录位置、Frontmatter 扩展、allowed-tools、Hooks、子 Agent、UI 组件、内置连接器 ID、专有变量运行时、平台审批）→ 缺失项映射为适配工作量。输出 7 种兼容状态之一；无加载/冒烟证据不得标 Compatible。

# 七、推荐与 Bundle 引擎

- 入口：项目模板（预置画像）或智能体个性化分析（对话式采集画像字段：行业、任务类型、目标平台、权限约束、预算、团队规模）。

- 召回排序：按任务标签召回 → 硬过滤（QUARANTINED/REMOVED/权限超限剔除；证据等级低于阈值降权）→ 按项目目标动态调整八维权重排序。

- 组合与冲突检测：触发重叠、权限叠加、依赖矛盾三类检测；组合级权限视图供用户确认。

- 输出三档 Bundle（轻量/平衡/增强），每项含职责、依赖、权限、限制、替代项与回退方案；安装动作一律跳转原始来源，不提供文件下载。

# 八、安全与合规设计

- 测试环境：强沙箱、无生产凭证、网络白名单、一次性环境、跨环境零串扰；恶意行为人工阻断通道。

- 数据边界：公开页面不泄露 Skill 正文、脚本与测试凭证；临时测试副本不对外提供；私有租户数据不进入公共搜索、推荐或统计。

- 高风险操作（删除、支付、发送、发布、审批、生产写入）一律人工确认（D-012）；首期不接真实支付与不可逆审批（NG-007）。

- 治理接口：评分撤回留审计、创作者纠错申诉、紧急停用、STALE 回归。

# 九、工程计划与工作量

| 模块 | 传统人天 | AI优先人天 | 压缩点 |
| --- | --- | --- | --- |
| 采集适配器×6 + 去重 | 35 | 12 | AI 生成解析器与适配器骨架 |
| 数据层 + 状态机 | 25 | 10 | Schema 与迁移脚本 AI 生成 |
| 静态检测流水线 | 30 | 11 | 规则集 AI 起草 + 人工审定 |
| 中立沙箱 + DSL + 测试员Agent | 45 | 18 | 任务脚本由 DSL 编译，AI 自愈选择器 |
| 判分与评分服务 | 35 | 13 | 断言库与裁判编排 AI 生成 |
| 前台 + 推荐 + 后台 | 45 | 17 | AI 生成页面与 CRUD，人管交互关键路径 |
| 合计 | 215 | 81 | 压缩率 62% |

里程碑映射：M1（第1月）= Phase 0 全部交付；M2（第2月）= 采集/静态/沙箱上线，开始批量中立测试；M3（第3月）= 评分/推荐/前台上线，达成 Phase 1 验收门（≥100 去重可运行 Skill 完成中立测试）。

**明确延期（本方案不设计、不预留接口）：Marketplace（付费交易与文件交付）、一键跨平台安装 —— 均延期至 Phase 3 单独立项。**
