"""最小任务步骤 DSL：TaskStep / TaskPlan。

字段留 None 时由 policy 在运行器内填默认值（timeout/network/workdir/env）。
纯数据，无行为。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class StepKind(str, Enum):
    RUN = "run"                                  # 运行命令（argv）
    SCRIPT = "script"                            # 运行内联脚本文本
    ASSERT_EXIT_CODE = "assert_exit_code"        # 断言上一步退出码
    ASSERT_OUTPUT_CONTAINS = "assert_output_contains"  # 断言上一步 stdout 含子串
    COPY_IN = "copy_in"                          # 注入输入文件（src->dst）
    COPY_OUT = "copy_out"                        # 取出产物（src->dst）


@dataclass(frozen=True)
class TaskStep:
    name: str
    kind: StepKind
    argv: tuple[str, ...] = ()          # RUN：命令与参数
    script_text: str | None = None      # SCRIPT：脚本正文
    expect_exit_code: int | None = None       # ASSERT_EXIT_CODE
    expect_substring: str | None = None       # ASSERT_OUTPUT_CONTAINS
    src: str | None = None              # COPY_IN/COPY_OUT
    dst: str | None = None
    timeout_sec: float | None = None    # None → policy 默认


@dataclass(frozen=True)
class TaskPlan:
    """一次沙箱运行的完整计划。network/workdir/env 为 None 时用 policy 默认。"""

    plan_id: str
    steps: tuple[TaskStep, ...]
    network: str | None = None          # "off" | "allowlist"；None → policy 默认
    workdir: str | None = None
    env: Mapping[str, str] | None = None
    labels: tuple[str, ...] = field(default_factory=tuple)  # 任务分类等展示用标签
