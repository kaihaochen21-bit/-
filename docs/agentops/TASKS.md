# 任务图

> 最后更新：2026-10-26

## TASK-006：Day 1 个性化样片 + 最终话术

- 状态：DONE
- 产物：
  - `projects/liuchunlin-demo/Day1_发送包_20261026.zip`
  - `projects/liuchunlin-demo/outreach/Day1_最终邮件与私信.md`
  - `projects/liuchunlin-demo/samples/mypip/mcp_project/video/第1话/final/第1话_1080p.mp4`
  - `projects/liuchunlin-demo/samples/agentvalley/mcp_project/video/第1话/final/第1话_1080p.mp4`
  - `projects/liuchunlin-demo/samples/qiaosi/mcp_project/video/第1话/final/第1话_1080p.mp4`
- 验收：
  - 4 个客户各有对应样片
  - 720p 预览均 <1.1MB（zCAD 1.68MB）
  - 联系方式卡均出现
  - 邮件/私信可直接复制

## TASK-009：AI 短剧/AI 视频需求扫描

- 状态：DONE
- 负责人：market-manager / orchestrator
- 依赖：无
- 产物：
  - `docs/agentops/RESEARCH.md`
  - `docs/agentops/LEADS.md`
  - `docs/agentops/REQUIREMENTS.md`
- 验收：
  - 有公开来源、原话、访问日期和联系路径
  - 有价格、能力缺口和明确的排除项
  - 区分事实、推断和未验证假设
  - 未发送任何外部消息
- 证据：
  - 页面复核：EPWK-1160947/1161045/1160833 显示“任务进行中”
  - 页面复核：Remote-China-2099/2210/2131 可访问
  - 线索表评分和排除项已落盘

## TASK-010：首轮样片与个性化首触包

- 状态：TODO
- 负责人：orchestrator / coder（如需要）
- 依赖：TASK-009、低成本渠道核验、用户确认首批线索
- 允许修改路径：`projects/ai-video-demand-outreach/`、`docs/agentops/`
- 验收：
  - 为 D006、D004、D005、D007 中至少 2 条制作对应样片或试剪片段
  - 每条样片 15–30 秒，可播放，有“概念样片/非官方”标识
  - 首触话术逐条定制，不群发
  - 发送前由用户本人确认
- 证据：样片路径、时长、分辨率、文件大小、话术版本

## TASK-011：发送、跟进与首单验证

- 状态：BLOCKED（等待用户确认是否发送）
- 负责人：orchestrator
- 依赖：TASK-010
- 验收：
  - 只联系用户批准的线索
  - 记录回复、预算、拒绝原因和下一次跟进时间
  - 至少争取 2 次沟通和 1 个付费试单
- 证据：沟通记录、报价范围、付款状态

## 后续

- TASK-007：Day 1 发送后记录回复
- TASK-008：第 4-5 天跟进刘春霖和 Day 1 未回复客户
## TASK-012：低成本渠道验证

- 状态：DONE
- 负责人：orchestrator
- 依赖：TASK-009
- 产物：`docs/agentops/CHANNELS.md`
- 验收：
  - 明确哪些渠道需要前会员费、哪些按次付费或免费申请
  - 一品威客因 VIP 门槛暂时降级
  - 给出 0–100 元预算内的 72 小时验证顺序
  - 不注册付费会员、不充值、不发送外联
- 证据：Upwork Connects 官方页、Freelancer.com 费用页、电鸭/Remote-China/猪八戒公开页访问记录

## TASK-013：《执光》AI视频制作投标文字方案

- 状态：REVIEW_READY
- 负责人：orchestrator
- 依赖：用户提供剧本、视频初稿、角色/场景/道具资产
- 产物：
  - `projects/ai_video_bid_20261108/执光_投标文字方案_v1.docx`
  - `projects/ai_video_bid_20261108/执光_投标文字方案_v1.md`
  - `projects/ai_video_bid_20261108/平台填写版_执光_v1.txt`
  - `projects/ai_video_bid_20261108/qa_render/执光_投标文字方案_v1.pdf`
- 验收：
  - 覆盖过往案例说明和制作方向两项投标内容
  - 明确撞脸明星、连贯性、转场、运镜、视听规律和16:9三分钟内要求
  - 不将客户提供的初稿冒充自有案例
  - DOCX 已完成6页PDF渲染检查，无页面越界或缺失章节
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-013 记录

## TASK-014：《心光如潮》10秒试稿分析与执行方案

- 状态：DELIVERED / AWAITING_CLIENT_REVIEW
- 负责人：orchestrator
- 依赖：用户已确认路线二和720p试稿；参考成片直链未取得，不影响文字风格执行
- 产物：
  - `projects/ai_video_bid_20261108/generation/final/心光如潮_10秒试稿_720p.mp4`
  - `projects/ai_video_bid_20261108/generation/心光如潮_10秒试稿_交付包_20261108.zip`
  - `projects/ai_video_bid_20261108/心光如潮_试稿执行方案_v1.md`
  - `projects/ai_video_bid_20261108/心光如潮_画面12-14原文.txt`
  - `projects/ai_video_bid_20261108/character_refs/`
- 验收：
  - 核对画面12–14与10秒试片可执行动作
  - 明确锁脸、原生动态、配音读音和短镜头拆分方法
  - 列出缺失信息、工期冲突、预算和返工风险
  - 已完成付费生成并按技术指标选片，API估算约25.05元
  - 已完成10秒720p成片、字幕、水印和本地质检；未对外发送
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-014 记录

## TASK-015：FormFunk 18 秒品牌创意广告

- 状态：DELIVERED / AWAITING_CLIENT_REVIEW
- 负责人：orchestrator
- 依赖：用户产品图；两条参考视频未收到
- 产物：
  - `projects/formfunk_ad_20261109/generation/final/FormFunk_蓝线生长_18秒品牌广告.mp4`
  - `projects/formfunk_ad_20261109/generation/FormFunk_蓝线生长_18秒广告_交付包_20261110.zip`
  - `projects/formfunk_ad_20261109/FormFunk_18秒创意分镜与提示词_v1.md`
- 验收：
  - 9:16、720×1280、24fps、18秒、英文字幕、声音和片尾字标
  - 产品花纹按 SIFT 匹配筛选，镜4A为产品英雄镜头
  - API估算约41.36元，低于65元上限
  - 未对外发送
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-015 记录

## TASK-016：即梦 API 半自动小说推文内容工厂

- 状态：IMPLEMENTED / VERIFIED_LOCAL
- 负责人：orchestrator
- 依赖：现有 `kling-image-mcp` 中的 Seedream/Seedance 客户端；火山方舟 `ARK_API_KEY`
- 产物：
  - `projects/novel_promo_factory/`：FastAPI 本地控制台、SQLite、素材检索、成本门控、渲染、发布包和线索记录
  - `projects/novel_promo_factory/jimeng_mcp/server.py`：只注册 Seedream/Seedance 的独立 MCP 入口
  - `projects/novel_promo_factory/start.bat`：双击启动
- 验收：
  - 程序不调用 Kling API，不读取 `KLING_API_KEY`
  - 只调用火山方舟即梦同源 Seedream/Seedance
  - Pexels/Pixabay 只用于素材检索
  - 默认 dry-run，付费生成必须人工确认
  - 单条 20 元、每月 600 元门控
  - 输出 9:16 视频、双平台封面、文案、许可证清单和发布清单
  - 人工发布后可回填链接、数据和客户线索
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-016 记录

## TASK-017：小说候选池、自动选书与人工审批

- 状态：IMPLEMENTED / VERIFIED_LOCAL
- 负责人：orchestrator
- 依赖：TASK-016
- 产物：
  - 小说候选池 CRUD
  - 自动选书：按类型、关键词、优先级和使用状态评分
  - 自动创建待审核项目并生成脚本/分镜
  - 人工“接受项目”或“拒绝并换一条”
  - 付费生成前强制检查项目已接受
- 验收：
  - 手动选择候选可创建待审项目
  - 自动选择从候选池取可用的自有/已授权小说
  - 拒绝后自动创建下一条候选
  - 接受前调用付费生成会被阻止
  - 不联网抓取小说平台内容
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-017 记录

## TASK-018：批量推荐项目与 Pixabay 图片素材回退

- 状态：IMPLEMENTED / VERIFIED_LOCAL
- 负责人：orchestrator
- 依赖：TASK-017、Pixabay API Key
- 产物：
  - `/api/projects/auto-batch`：批量创建 3–5 个待审项目并搜集素材
  - Pixabay 图片搜索与竖版图片候选下载
  - 素材错误日志 API Key 脱敏
- 验收：
  - 批量项目默认停在 `pending_approval`
  - 每个项目生成 8 个分镜并搜集 3 个候选图片
  - 批量按钮不调用付费即梦 API
  - 素材错误不会在日志中暴露 `key=`
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-018 记录

## TASK-019：安装 eternityspring/shuohao-skills

- 状态：DONE
- 负责人：orchestrator
- 来源：`eternityspring/shuohao-skills`，提交 `8af10e0ea1a550e4575666884f4deef780bf38ff`，Apache-2.0。
- 产物：
  - `C:\Users\陈楷浩\.codex\skills\character-refs`
  - `C:\Users\陈楷浩\.codex\skills\novel-art`
  - `C:\Users\陈楷浩\.codex\skills\novel-characters`
  - `C:\Users\陈楷浩\.codex\skills\novel-outline`
  - `C:\Users\陈楷浩\.codex\skills\novel-script`
  - `C:\Users\陈楷浩\.codex\skills\novel-staging`
  - `C:\Users\陈楷浩\.codex\skills\novel-storyboard`
- 验收：7 个技能均有 `SKILL.md`；安装文件与审查源 113 个文件哈希一致；7 个自带自测共 1,559 项断言通过。
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-019 记录。

## TASK-020：本机豆包客户端调用 Shuohao Short Drama 生成样片

- 状态：DONE / VIDEO_GENERATED / VERIFIED_LOCAL
- 负责人：orchestrator
- 目标：连接本机豆包桌面客户端，让豆包加载 `shuohao-skills` 工作流，生成剧本和视频样片。
- 实现方式：通过 Windows UI Automation 操作豆包客户端；未使用官方 API。
- 产物：
  - `projects/doubao_shuohao_sample/最后一单_10秒_9x16_720p.mp4`
  - `projects/doubao_shuohao_sample/最后一单_剧本分镜.md`
  - `projects/doubao_shuohao_sample/最后一单_预览拼图.jpg`
  - `projects/doubao_shuohao_sample/README.md`
- 验收：视频为 720×1280、9:16、24fps、10.08 秒、H.264 + AAC；FFmpeg 全片解码返回码 0。
- 说明：豆包回复确认已读取技能中的 `SKILL.md`；视频生成消耗每日免费额度，界面未显示额外付费金额。

## TASK-021：豆包免费视频额度核查

- 状态：DONE / SOURCE_CONFLICT_RECORDED
- 负责人：orchestrator
- 目标：确认豆包个人版免费视频额度的消耗与每日可生成时长。
- 结论：官方订阅页只写“图片与视频生成，满足日常使用次数”，未公开精确换算；常见口径为每天约 10 个视频额度、5 秒 1 个、10 秒 2 个，保守产能约 50 秒/天。
- 证据：见 `docs/agentops/DOUBAO_QUOTA.md`。


## TASK-022：豆包免费额度任务桥与《最后一班地铁》50 秒成片

- 负责人：orchestrator
- 状态：DONE
- 依赖：TASK-016、TASK-020、TASK-021
- 目标：把本机豆包桌面端免费视频生成接入半自动网站，生成 5×10 秒镜头、拼接、加原创音乐和中文字幕。
- 允许修改：`projects/novel_promo_factory/app/`、`projects/novel_promo_factory/tests/`、`projects/novel_promo_factory/tools/`、项目内容目录和相关 AgentOps 文档。
- 验收：
  - 网站存在任务计划、状态、导入和专用渲染接口。
  - 5 个镜头均为 10 秒左右，成片为 50.00 秒、1080×1920、30fps、H.264 + AAC。
  - 成片全片 FFmpeg 解码成功，音频不是静音。
  - 原始 30 秒分镜有备份。
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-022 记录。
- 限制：豆包免费额度在完成第 4 条豆包镜头后耗尽，第 5 段使用本地后期收尾镜头；前 4 段为豆包生成。

## TASK-023：AI 短剧情报雷达

- 状态：IMPLEMENTED / VERIFIED_LOCAL
- 负责人：orchestrator / coder / tester
- 分支：`codex/TASK-023-ai-drama-radar`
- 目标：在现有 FastAPI/SQLite 内容工厂中增加情报雷达，后台定期采集 GitHub 与官方公开来源。
- 产物：
  - `projects/novel_promo_factory/app/radar.py`
  - `projects/novel_promo_factory/app/radar_cli.py`
  - `projects/novel_promo_factory/app/static/` 中的雷达页面
  - `projects/novel_promo_factory/enable_radar_task.bat`
  - `projects/novel_promo_factory/disable_radar_task.bat`
  - `projects/novel_promo_factory/scripts/install_radar_task.ps1`
  - `projects/novel_promo_factory/scripts/uninstall_radar_task.ps1`
  - `projects/novel_promo_factory/radar_notify.ps1`
- 验收：
  - 首次扫描只建立快照，不显示虚假历史增长。
  - 12–36 小时内的最近快照可换算 24 小时 Star 增量。
  - 支持仓库、官方新闻、页面更新、评分筛选、状态标记和日报。
  - GitHub 限流、RSS/HTML 失败时保留已完成结果并记录错误。
  - 不读取付费生成密钥、不安装第三方 Skill、不发起外部写操作。
- 证据：见 `EVIDENCE.md` 的 TASK-023 记录。

## TASK-024：场景声音引擎（MeloTTS + ACE-Step + Freesound）

- 负责人：orchestrator
- 状态：IMPLEMENTED / VERIFIED_LOCAL
- 依赖：TASK-016、TASK-022
- 目标：给每个镜头分别规划并生成旁白、背景音乐和环境音/音效，混音后输出可发布 MP4。
- 允许修改：`projects/novel_promo_factory/app/`、`tests/`、`audio_services/`、启动脚本、项目 README 和 AgentOps 文档。
- 产物：
  - `app/sound.py`：声音方案、MeloTTS/ACE-Step/Freesound 适配、本地回退和 FFmpeg 分层混音。
  - `audio_services/melotts_server.py`：MeloTTS 本地 HTTP 服务。
  - `setup_audio_runtime.bat`、`start_audio_services.bat`、`start_ace_step.bat`、`start_melotts.bat`。
  - `.env.example` 和项目 README 配置说明。
  - `/sound/status`、`/sound/plan`、`/sound/generate`、`/sound/render` API 以及网页操作面板。
- 验收：
  - 每个镜头产生独立的旁白、音乐和 SFX 计划。
  - 外部服务不可用时显式记录回退，不伪造生成成功。
  - 场景混音成片保留原视频流并替换为分层音频。
  - 最终 MP4 自动复制到发布成片库。
  - 自动化测试覆盖声音计划、回退生成、混音和 API。
- 证据：见 `docs/agentops/EVIDENCE.md` 的 TASK-024 记录。
- 限制：Freesound 需要用户自己申请免费 API Key；ACE-Step/MeloTTS 首次安装和模型下载体积较大。

## TASK-025：AI 短剧雷达自动精选与安全安装

- 状态：IMPLEMENTED / VERIFIED_LOCAL
- 分支：`codex/TASK-025-radar-auto-curation`
- 目标：自动从高相关候选中选出少量最值得关注的项目，并直接安装通过静态安全审查的标准 Skill。
- 产物：
  - `app/radar_curation.py`
  - 自动精选、安装记录和资格检查数据库表
  - `/api/radar/curate` 与 dashboard 精选/安装记录
  - 网页“今日自动精选”和“最近自动安装的 Skill”
  - 日报自动精选与安装记录章节
- 验收：
  - 每次扫描自动生成 3 项精选，不需要人工先挑。
  - 每日最多安装 1 个新 Skill。
  - 非根目录 Skill、许可证不明、危险模式、超限或路径不安全项目不会安装。
  - 自动安装使用 GitHub 官方 ZIP 归档，不执行仓库脚本。
  - 已安装 Skill 可追溯到仓库、许可证、路径和安装时间。

## TASK-026：会替人做梦的便利店 60 秒发布版

- 状态：DONE（本地验证）
- 负责人：orchestrator
- 目标：基于前片复盘，使用豆包免费视频额度制作更真实、竖屏可发布的都市奇幻短片，并完成字幕、旁白、音乐、音效和发布文件。
- 产物：
  - `projects/会替人做梦的便利店_60秒_交付/会替人做梦的便利店_60秒_1080x1920_可发布.mp4`
  - `projects/抖音发布_成片库/会替人做梦的便利店_60秒_9x16_1080p_可发布.mp4`
  - `projects/会替人做梦的便利店_60秒_交付/制作说明.md`
  - `projects/会替人做梦的便利店_60秒_交付/发布文案.md`
  - `projects/novel_promo_factory/content/f1497c20b328/doubao_batch/source_manifest.json`
- 验收：
  - 画面避开前片冷绿烟雾、透明手、夸张特效等问题。
  - 交付 60.10 秒成品，可全片解码，字幕、音轨、响度均通过检查。
  - 未把重复或本地补镜冒充豆包新视频。
  - 保留第 5、6 镜提示词，额度恢复后可继续替换为纯豆包版本。
- 限制：当天豆包只确认到 4 段唯一视频；60 秒版为 4 段豆包 + 2 段本地后期补镜。



## TASK-027：三个推荐 AI 短剧项目本机部署（2026-11-15）

- 状态：VERIFIED_LOCAL
- 分支：`codex/TASK-027-deploy-recommended-apps`
- 负责人：orchestrator
- 范围：
  - `projects/deployed_apps/awesome-short-drama-skills`
  - `projects/deployed_apps/huobao-drama-ai`
  - `projects/deployed_apps/openmontage`
  - `projects/deployed_apps` 下的统一启动、停止和说明文件
- 验收：
  - 三个本机入口均返回 HTTP 200。
  - Huobao 中文页、SQLite、健康检查和本地管理员登录正常。
  - OpenMontage 生产前端、FastAPI 健康检查和 Demo 登录正常。
  - Awesome Short Drama Skills 静态站完成生成并可浏览。
  - 停止后重新执行统一启动脚本，三个服务仍全部恢复。
  - 不读取或传递 ARK、Kling、OpenAI 等付费密钥。
  - 第三方源码、虚拟环境、数据库、日志和归档不进入 Git。
- 当前边界：
  - 仅监听 `127.0.0.1`，未发布公网。
  - OpenMontage 当前没有可用的 FFmpeg 和视频生成后端；不宣称视频合成链路已验证。
  - 未配置任何付费模型 Key。

- Git：本地提交 `2a2ba4f`；推送 `origin/codex/TASK-027-deploy-recommended-apps` 因 GitHub HTTPS 连接重置失败，远程分支尚未更新。
