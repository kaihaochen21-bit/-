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
| `imageio-ffmpeg` | https://github.com/imageio/imageio-ffmpeg | 0.8.1 | BSD-2-Clause | pip 用户安装 | orchestrator | 已用于本地视频封装，不随交付分发 |
| OpenCV Zoo YuNet / SFace | https://github.com/opencv/opencv_zoo | 2023mar / 2021dec 模型文件 | Apache-2.0 | 下载 ONNX 模型到项目 `.models/` | orchestrator | 面部一致性质检，不随最终成片分发 |
| `eternityspring/shuohao-skills` | https://github.com/eternityspring/shuohao-skills | `main@8af10e0ea1a550e4575666884f4deef780bf38ff` | Apache-2.0 | 经审核后复制到 `%USERPROFILE%\.codex\skills`，未执行仓库安装脚本 | orchestrator | 已安装 7 个短剧技能；`character-refs` 出图可能消耗订阅/API 额度 |
| ACE-Step 1.5 | https://github.com/ace-step/ACE-Step-1.5 | `ca1e85fe9430179831e6bc6be790c332190a3866` | MIT | 本地独立运行时，不复制进网站仓库 | orchestrator | 场景音乐生成适配器 |
| MeloTTS | https://github.com/myshell-ai/MeloTTS | `209145371cff8fc3bd60d7be902ea69cbdb7965a` | MIT | 本地独立运行时，不复制进网站仓库 | orchestrator | 已安装并用于中文旁白生成；独立 Python 3.11 运行时 |
| Freesound API | https://freesound.org/docs/api/ | API v2 | 各音效独立授权 | 用户申请 Key，默认只筛选 CC0 | orchestrator | 环境音/音效检索与预览下载 |

## 强制规则

- 固定版本或提交，不跟踪浮动主分支。
- 优先使用包管理器或 Git submodule；默认不复制第三方代码。
- 不执行来源不明的 `install`、PowerShell、Shell 或二进制脚本。
- 记录许可证、维护状态、依赖、权限和撤销方式。
- 引入前进行安全检查和最小权限测试。
