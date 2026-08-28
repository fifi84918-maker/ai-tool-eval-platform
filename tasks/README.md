# tasks/ 目录 — 指挥官与 dsh 的协作交换区

## 工作流
1. 指挥官（AI）将任务 prompt 写入 current_prompt.md
2. 执行：dsh < tasks/current_prompt.md > tasks/last_output.md 2>&1
3. 指挥官读取 tasks/last_output.md 审查结果
4. 审查通过后，last_output.md 内容可备份到 prev_output.md

## 注意
- current_prompt.md 每次覆盖写入新任务，不累积
- last_output.md 每次执行前自动覆盖
- 不要手动编辑 last_output.md，由 dsh 输出生成
