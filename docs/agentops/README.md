# AgentOps 文档索引

主智能体必须先读取 `PROJECT.md`、`STATE.md`、`TASKS.md` 和 `DECISIONS.md`，再按当前阶段读取其他文档。

| 文档 | 作用 | 主要维护者 |
|---|---|---|
| `PROJECT.md` | 项目合同、范围、交付物和成功标准 | orchestrator |
| `RESEARCH.md` | 市场、用户、竞品和复用研究 | market-manager |
| `REQUIREMENTS.md` | 可测试需求和验收标准 | requirements-analyst |
| `ARCHITECTURE.md` | 架构、接口、数据流和测试策略 | architect |
| `TASKS.md` | 任务图、负责人、状态和证据索引 | orchestrator |
| `STATE.md` | 当前状态、阻塞和恢复入口 | orchestrator |
| `DECISIONS.md` | 重要决策与 ADR | 主责智能体 |
| `EVIDENCE.md` | 命令、结果、产物和验收证据 | tester / coder |
| `OPEN_SOURCE.md` | 开源工具和依赖的引入规则 | orchestrator |
| `GITHUB_WORKFLOW.md` | 分支、PR、CI 和合并规则 | orchestrator |

文档必须保持真实、简洁、可恢复。不要把整段对话复制进文档，只记录后续智能体继续工作所需的事实。

## 角色指令源

`.codex/agents/*.toml` 是六个角色的权威指令源。由于应用层子智能体工具可能只接收任务提示词，主智能体派发前必须读取对应 TOML 的 `developer_instructions`，并将其与任务卡一起传入子智能体，不能只传角色名称。