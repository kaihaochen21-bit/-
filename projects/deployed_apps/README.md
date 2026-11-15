# 三个 AI 短剧推荐项目本机部署

部署日期：2026-11-15
部署范围：仅本机 `127.0.0.1`，没有发布到公网。

## 一键使用

- 双击 `start_all.bat`：启动三个服务并打开三个网页。
- 双击 `open_all.bat`：服务已启动时，只重新打开网页。
- 双击 `stop_all.bat`：停止三个已部署服务。

启动脚本会清空进程内的常见付费模型密钥变量，不会把现有 ARK、Kling、OpenAI 等密钥传给这三个应用。每次启动的日志和 PID 保存在 `run/`，该目录不会提交。

## 访问入口

| 项目 | 本机地址 | 当前状态 | 本地登录/入口 |
|---|---|---|---|
| Huobao Drama AI | http://127.0.0.1:3001/ | 已运行，SQLite 数据库正常 | 管理员：`admin@huobao.local` / `admin123` |
| OpenMontage Drama Studio | http://127.0.0.1:8787/ | 已运行，单进程文件存储模式 | 页面点击 Demo；Demo 账号信息由页面显示 |
| Awesome Short Drama Skills | http://127.0.0.1:3002/ | 已生成并运行静态站 | 直接浏览，无需登录 |

## 三个项目分别是什么

### 1. Huobao Drama AI

Next.js 全栈 AI 短剧制作台，包含剧本、角色、场景、分镜、图片、视频、TTS、项目流水线和成本统计等模块。

本机能力：

- 中文和英文页面可访问；根地址会转到中文页 `/zh-CN`。
- 使用本地 SQLite：`huobao-drama-ai/prisma/db/custom.db`。
- 管理员账号已创建，登录 API 已验证成功。
- 不上传素材、不配置供应商 Key 时，仍可使用提示词、项目管理、手动导入和本地工作流页面。
- 实际调用图片、视频、TTS 或大模型供应商前，需要你在设置页自行配置免费或付费 Key；本次没有读取或写入你的付费密钥。

已知限制：

- Next.js 16.3.1 的国际化路由与项目原始的 `as-needed` 配置会产生重定向循环。本部署已把语言前缀改为 `always`，并把中间件迁移为 `proxy.ts`，因此中文固定入口是 `/zh-CN`。
- 这是本地管理员演示密码，只适合当前本机访问；开放到局域网或公网前必须更换。

### 2. OpenMontage Drama Studio

React/Vite 前端 + FastAPI 后端的 AI 短剧制片台，包含剧本、角色、场景、道具、分镜、画布、配音和剪辑工作台。

本机能力：

- 前端已完成生产构建，后端 `/api/health` 返回正常。
- 使用本地磁盘保存项目；没有使用 Docker。
- 使用进程内任务池，不依赖 Redis、MinIO 或 PostgreSQL。
- 本地 Demo 登录已启用，`STUDIO_REQUIRE_GITHUB_STAR=0`，不要求 GitHub 点星。
- 健康检查把 Pollinations 列为免 Key 的文本/图片候选后端；实际调用仍受外部服务可用性影响。
- Edge TTS 已安装，属于免 Key 的本地接口路径。

已知限制：

- 当前机器没有发现可用的 FFmpeg，OpenMontage 健康检查显示 `ffmpeg: false`。界面、项目管理、剧本/分镜编辑可以运行，但视频合成/剪辑相关步骤需要后续安装 FFmpeg。
- 没有配置 Seedream、Seedance、ComfyUI 或其他视频生成后端，所以不会自动产生付费视频。
- PostgreSQL、Redis、MinIO 未启用；适合单机使用，不是多用户生产部署。

### 3. Awesome Short Drama Skills

这是一个精选目录，不是单一可执行业务系统。它整理了 86 个短剧 Skill 项目和 16 个相关开源平台，并提供安装指南、实测记录、阶段/模型/类型索引。

本机能力：

- 已使用项目自带的标准库构建器生成 1,325 个中英文页面。
- 可通过本地站点浏览全部索引、项目和指南。
- 没有把 86 个 Skill 全部装进你的 Codex；目录中的项目是否安全、是否需要脚本，仍需逐项查看许可证和 `SKILL.md`。

## 目录与运行边界

```text
projects/deployed_apps/
  awesome-short-drama-skills/   第三方静态目录源码和 web/dist
  huobao-drama-ai/              Next.js 源码、依赖和 SQLite
  openmontage/                  OpenMontage 源码、前端 dist 和本地项目
  .tools/node-v24.22.1-win-x64/ 本地 Node/npm 运行时
  .venvs/openmontage/           OpenMontage Python 虚拟环境
  run/                          PID、日志和演示密钥
  start_all.ps1
  start_all.bat
  stop_all.ps1
  stop_all.bat
  open_all.bat
```

第三方源码、`node_modules`、Python 虚拟环境、数据库、日志和 ZIP 归档都通过 `projects/deployed_apps/.gitignore` 排除在 Git 提交之外，只提交启动脚本、说明和忽略规则。

## 重新构建时需要什么

- Node 运行时：`projects/deployed_apps/.tools/node-v24.22.1-win-x64/node.exe`，npm 版本 11.19.1。
- Python：OpenMontage 虚拟环境使用 Python 3.12.10。
- Huobao 重建前端时使用 `npx next build`，不要使用其 `npm run build`，因为后者的构建脚本会恢复 PostgreSQL schema。
- OpenMontage 前端重建：进入 `openmontage/studio`，运行 `npm run build`。
- Awesome 静态站重建：在 `awesome-short-drama-skills` 运行 `python scripts/build_site.py`。

## 许可证

| 项目 | 许可证 | 来源 |
|---|---|---|
| UnderleveledBuilder/awesome-short-drama-skills | CC0-1.0 | https://github.com/UnderleveledBuilder/awesome-short-drama-skills |
| dav-niu474/huobao-drama-ai | MIT | https://github.com/dav-niu474/huobao-drama-ai |
| charliewwdev/OpenMontage | AGPL-3.0 | https://github.com/charliewwdev/OpenMontage |

OpenMontage 是 AGPL-3.0：本机使用可以，但如果修改后向网络用户提供或分发，需要按许可证履行对应义务。三个项目原有的许可证文件均保留在各自源码目录。

## 信息来源

- [Huobao Drama AI](https://github.com/dav-niu474/huobao-drama-ai) — 访问时间：2026-11-15
- [OpenMontage](https://github.com/charliewwdev/OpenMontage) — 访问时间：2026-11-15
- [OpenMontage 自托管说明](https://github.com/charliewwdev/OpenMontage/blob/main/docs/SELF_HOSTING_zh-CN.md) — 访问时间：2026-11-15
- [Awesome Short Drama Skills](https://github.com/UnderleveledBuilder/awesome-short-drama-skills) — 访问时间：2026-11-15
