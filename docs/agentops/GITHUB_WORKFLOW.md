# Git 与 GitHub 工作流

## 分支

- 主分支：`main`
- 功能分支：`agent/<task-id>-<short-slug>`
- 初始化完成后，智能体不得直接向 `main` 提交。
- 并行编码使用独立 worktree 和互不重叠的允许修改路径。

## 提交

```text
type(scope): summary [TASK-ID]
```

允许的 `type`：`feat`、`fix`、`refactor`、`test`、`docs`、`chore`、`ci`。

## Pull Request

PR 必须包含：

- 任务 ID 与目标
- 改动摘要
- 验收条件
- 测试命令和真实结果
- 风险、限制和回滚方式
- 文档更新情况
- 未验证项

## 合并策略

- 使用 PR，禁止直接推送到 `main`。
- CI 必须通过。
- 人工审核后由用户合并。
- 不启用自动合并、不自动发布、不自动部署。
- 分支保护不可用时，至少保持“PR + 人工合并”的约定，并把配置缺失写入 `STATE.md`。

## 恢复

如果 GitHub 插件、OAuth 或网络不可用：

1. 保留本地功能分支和提交。
2. 在 `STATE.md` 记录阻塞和需要用户完成的动作。
3. 不得声称远程仓库或 PR 已创建。