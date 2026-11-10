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
