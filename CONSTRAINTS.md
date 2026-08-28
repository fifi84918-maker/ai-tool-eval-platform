# 项目约束（所有任务必须遵守）

1. 不修改 analyzer/scoring/ 内部逻辑
2. 不引入新依赖（用已有生态）
3. 现有测试不回退
4. 增量加，不重构现有代码
5. 每次修改后确认 git status 干净再 commit
6. 测试目标：201 passed（当前 28 passed，待修复）
