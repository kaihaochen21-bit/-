# 系统架构

> 状态：TASK-016 已实现
> 最后更新：2026-11-10
> 负责人：orchestrator

## 系统上下文

`projects/novel_promo_factory` 是 Windows 本地单用户内容工厂。输入小说文本后，生成脚本/分镜，检索 Pexels/Pixabay 免费素材，调用火山方舟即梦同源 Seedream/Seedance，使用 Edge TTS 和 FFmpeg 合成 9:16 视频，最后生成抖音/小红书发布包并记录客户线索。

## 组件与职责

| 组件 | 职责 | 输入 | 输出 | 依赖 |
|---|---|---|---|---|
| FastAPI 控制台 | 本地网页、项目/任务/线索管理 | 浏览器请求 | JSON/文件 | FastAPI、SQLite |
| 脚本模板 | 生成本地 5 段式脚本和分镜 | 标题、类型、文本 | script/shots | 无外部 LLM |
| StockService | Pexels/Pixabay 搜索、下载、许可证记录 | 镜头关键词 | 本地候选素材 | Pexels/Pixabay API |
| Jimeng MCP Client | 通过 stdio 调用即梦-only MCP | 生成参数 | 图片/视频任务 | MCP、ARK_API_KEY |
| jimeng_mcp | 只注册 Seedream/Seedance 工具 | 工具调用 | 生成结果 | 火山方舟 |
| Media | Edge TTS、FFmpeg、字幕、封面 | 分镜和素材 | MP4、JPG、SRT | Edge TTS、FFmpeg |
| Package | 双平台发布包、许可证和 AI manifest | 成片、成本、素材 | publish/ 文件 | 本地文件系统 |
| SQLite | 项目、素材、成本、发布、线索 | CRUD | 查询结果 | sqlite3 |

## 公共接口

| 接口 | 类型 | 输入 | 输出 |
|---|---|---|---|
| `POST /api/projects` | HTTP | 标题、类型、文本、授权状态 | 项目 |
| `POST /api/projects/{id}/script/auto` | HTTP | 项目 ID | 脚本和分镜 |
| `POST /api/projects/{id}/asset-search` | HTTP | 项目 ID | 候选素材和警告 |
| `POST /api/projects/{id}/generate/dry-run` | HTTP | 项目 ID | 成本估算 |
| `POST /api/projects/{id}/generate/confirm` | HTTP | `confirmed=true` | Seedream/Seedance 结果 |
| `POST /api/projects/{id}/render` | HTTP | 项目 ID | MP4/封面/SRT |
| `POST /api/projects/{id}/package` | HTTP | 项目 ID | 发布包 |
| `POST /api/posts/{id}/published` | HTTP | 发布链接、指标 | 发布记录 |
| `POST /api/leads` | HTTP | 客户和需求 | 线索 |

## 数据流

1. 浏览器 -> FastAPI -> SQLite 创建项目。
2. 本地模板 -> script/shots -> SQLite。
3. 镜头关键词 -> Pexels/Pixabay -> 本地素材 + 许可证 JSON。
4. dry-run -> 成本门控 -> 用户确认 -> 即梦-only MCP -> Seedream/Seedance。
5. 素材/生成结果 -> Edge TTS + FFmpeg -> master_9x16.mp4。
6. 成片/封面/文案/许可证 -> publish/ -> 用户人工上传。
7. 发布链接/指标/客户线索 -> SQLite -> dashboard。

## 技术选型

| 领域 | 选择 | 理由 |
|---|---|---|
| Web | FastAPI + 原生 HTML/JS | 本地轻量、易双击启动 |
| 数据库 | SQLite | 单用户、零部署 |
| 图片/视频 | 火山方舟 Seedream/Seedance | 用户指定即梦同源 API |
| 免费素材 | Pexels/Pixabay | 免费 API、适合视频混剪 |
| 配音 | Edge TTS | 本地免费、无需额外 LLM API |
| 剪辑 | imageio-ffmpeg | 免安装、可本地渲染 |
| 发布 | 人工上传 | 避免平台登录和风控 |

## 失败模式与恢复

| 失败 | 检测 | 影响 | 恢复 |
|---|---|---|---|
| `ARK_API_KEY` 缺失 | 健康检查 | 不能生成 | 显示配置提示 |
| Pexels/Pixabay 限流 | HTTP 错误 | 无法自动找素材 | 缓存/手动素材回退 |
| Seedance 超时 | 任务查询超时 | 单镜头失败 | 保留 task_id，稍后查询 |
| FFmpeg 字幕失败 | 命令非零退出 | 字幕未烧录 | 输出无字幕版本 |
| 素材许可证缺失 | 打包前校验 | 禁止发布包 | 补齐许可证 |
| 预算超限 | dry-run/confirm | 阻止付费 | 降低镜头或换成免费素材 |

## TASK-017 补充：小说候选池

- 新增 `novel_candidates` 表，记录标题、类型、正文、授权状态、标签、优先级、审核/使用状态。
- 自动选书按类型、关键词、优先级和使用次数评分；只从用户录入的候选池选择。
- 自动创建的项目先进入 `pending_approval`，用户接受后才允许付费生成；拒绝后可自动切换下一条候选。
- 候选和项目决策均保存在 SQLite，不联网抓取小说平台。

## TASK-023 补充：AI 短剧情报雷达架构

- `RadarCollector` 读取 GitHub Search、候选仓库 README/SKILL.md、OpenAI RSS、Kling/Runway/MiniMax/火山方舟页面。
- `RadarScorer` 执行相关性、24 小时 Star 增长、近期活跃、可信度和降本评分；首次扫描输出 `growth_baseline=true`。
- SQLite 新增 `radar_items`、`radar_repo_snapshots`、`radar_runs`、`radar_source_state`，不改动内容工厂原有项目表。
- `radar_cli.py` 提供计划任务入口 `python -m app.radar_cli scan --scheduled`，并使用文件锁防止并发扫描。
- FastAPI 新增雷达 dashboard、扫描、状态更新和日报接口；网页增加“内容工厂 / AI 情报雷达”切换。
- 外部读取均使用公开 GET 请求，不写入第三方平台；通知只调用本机 PowerShell 气泡提示。

## TASK-025 补充：自动精选与安全安装架构

- `radar_curation.py` 负责精选排序、安装资格判断、ZIP 安全下载/解压、静态扫描、目标目录安装和安装记录。
- 精选采用分数优先 + 类型多样化，自动生成 3 项；安装候选最多扫描 6 个 Skill 候选，每天最多安装 1 个。
- 只有仓库根目录 `SKILL.md` 可作为自动安装单元；嵌套 Skill 合集目前只推荐，不自动展开安装。
- 安装源使用 `codeload.github.com/<repo>/zip/HEAD` 官方归档，禁止路径穿越和符号链接。
- SQLite 新增 `radar_curation` 和 `radar_installs`，保存理由、状态、来源、许可证、路径和时间。
