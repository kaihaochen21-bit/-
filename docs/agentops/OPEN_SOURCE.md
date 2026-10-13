# 开源能力引入规则

## 选择顺序

1. Codex 原生能力。
2. 项目已有 Skill、脚本和模板。
3. 已安装且已审核的插件或 MCP。
4. 官方或高信誉白名单来源。
5. 自行编写最小实现。

## 默认白名单

| 名称 | 类型 | 许可证 | 用途 | 默认状态 |
|---|---|---|---|---|
| `github@openai-api-curated` | Codex 插件 | MIT | 仓库、PR、Issue、CI | 推荐安装 |
| `superpowers@openai-api-curated` | Codex 插件 | MIT | 规划、TDD、调试、子智能体协作 | 推荐安装 |
| `build-web-apps@openai-api-curated` | Codex 插件 | MIT | Web 前端和浏览器测试 | 按项目启用 |
| `game-studio@openai-api-curated` | Codex 插件 | MIT | 浏览器游戏开发 | 按项目启用 |

`codex-security` 和 `data-analytics` 等非 MIT 插件不能因为“方便”自动安装；必须先确认许可证、账号要求和数据权限。

## 引入记录

| 名称 | 来源 URL | 版本/提交 | 许可证 | 引入方式 | 审核人 | 状态 |
|---|---|---|---|---|---|---|
| 待填写 | 待填写 | 待填写 | 待填写 | 包管理器/子模块/插件/Skill | 待填写 | 待审核 |

## 强制规则

- 固定版本或提交，不跟踪浮动主分支。
- 优先使用包管理器或 Git submodule；默认不复制第三方代码。
- 不执行来源不明的 `install`、PowerShell、Shell 或二进制脚本。
- 记录许可证、维护状态、依赖、权限和撤销方式。
- 引入前进行安全检查和最小权限测试。