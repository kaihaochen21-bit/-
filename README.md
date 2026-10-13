# Codex AgentOps 多智能体项目模板

这个目录是一套通用项目工作台。你只需要给出最终目标，主智能体就会读取文档、判断所需能力、组织市场、需求、架构、编码和测试智能体，管理 Git 分支与 PR，最后汇总完整项目交付。

## 快速开始

### 方式一：在 Codex 中使用

在当前项目对话中输入：

```text
$agentops 最终目标：<你的目标>
```

主智能体会先读取项目文档，再决定是否需要一次规格确认。没有关键歧义时，它会连续执行到完成或触发风险门控。

### 方式二：Windows 双击

- `start-agentops.cmd`：在当前模板项目启动主智能体。
- `new-agentops-project.cmd`：复制模板到新目录，初始化 Git，并开始一个新项目。

两个入口都会用中文提示输入目标，不需要记 CLI 参数。

## 六个核心智能体

| 智能体 | 主要职责 |
|---|---|
| `orchestrator` | 主控、文档、能力选择、调度、Git、集成、最终交付 |
| `market-manager` | 市场、用户、竞品、替代方案和复用机会 |
| `requirements-analyst` | 范围、需求、用户故事、验收标准 |
| `architect` | 架构、接口、数据流、技术选型和 ADR |
| `coder` | 在独立分支/worktree 中实现和自测 |
| `tester` | 独立复现、边界、回归、安全和证据记录 |

## 首次使用前提

1. 运行 `codex doctor`，确保 Codex、Git、沙箱和网络状态正常。
2. 配置 Git 用户名和邮箱：
   ```powershell
   git config --global user.name "你的名字"
   git config --global user.email "你的邮箱"
   ```
3. 如需自动创建 GitHub 仓库和 PR，安装并登录 GitHub 插件：
   ```powershell
   codex plugin add github@openai-api-curated
   ```
4. 第一个项目完成前，建议先运行验证：
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agentops.ps1 -Mode Verify
   ```

## 重要边界

- 智能体可以创建功能分支和 PR，但不会自动合并 `main`。
- 涉及付费、删除、发布、部署、权限和密钥时，必须人工确认。
- 第三方 Skill、插件和项目只从白名单或审核记录中引入。
- 当前 Windows 沙箱若未修复，不能把系统当成无人值守执行环境。