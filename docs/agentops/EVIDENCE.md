# 证据记录

> 最后更新：2026-10-26

## Day 1 样片

### zCAD AI

- 1080p：`samples/zcad/mcp_project/video/第1话/final/第1话_1080p.mp4`
- 17.48 秒、1080×1920、30fps、4,549,712 bytes
- 720p 预览：`samples/zcad/zcad_预览_720p.mp4`（1,680,400 bytes）

### myPip

- 1080p：`samples/mypip/mcp_project/video/第1话/final/第1话_1080p.mp4`
- 19.84 秒、1080×1920、30fps、2,733,015 bytes
- 720p 预览：`samples/mypip/mypip_预览_720p.mp4`（890,972 bytes）
- 联系方式卡哈希距离：3

### AgentValley

- 1080p：`samples/agentvalley/mcp_project/video/第1话/final/第1话_1080p.mp4`
- 17.11 秒、1080×1920、30fps、3,571,643 bytes
- 720p 预览：`samples/agentvalley/agentvalley_预览_720p.mp4`（1,068,822 bytes）
- 联系方式卡哈希距离：6

### 巧思工具箱

- 1080p：`samples/qiaosi/mcp_project/video/第1话/final/第1话_1080p.mp4`
- 15.87 秒、1080×1920、30fps、3,833,182 bytes
- 720p 预览：`samples/qiaosi/qiaosi_预览_720p.mp4`（1,067,937 bytes）
- 联系方式卡哈希距离：3

## Day 1 发送包

- ZIP：`projects/liuchunlin-demo/Day1_发送包_20261026.zip`（5,469,815 bytes）
- 内含：4 条 720p 样片、作品集一页版、最终邮件/私信、执行清单、刘春霖已发送说明

## 未验证/限制

- 未实际发送 Day 1 的 4 个新客户
- 回复率需发送后统计
## TASK-009 需求扫描证据（2026-10-26）

### 页面复核

- `https://m.epwk.com/task/1160947/`：HTTP 200，页面显示“任务进行中”，标题“剪辑视频等”，预算 ¥1,000–3,000，需求含 15–60 秒剪辑、字幕、音效、调色、封面和工程归档。
- `https://m.epwk.com/task/1161045/`：HTTP 200，页面显示“任务进行中”，标题“游戏视频定制推广引流”，预算 ¥1,000–3,000。
- `https://m.epwk.com/task/1160833/`：HTTP 200，页面显示“任务进行中”，标题“需要AI白模预演动画制作”，页面标价 ¥10,000–20,000。
- `https://remote-china.com/jobs/2099`、`/2210`、`/2131`：页面可访问，分别显示广告营销 AI 视频、AI 短剧/MV、出海 AI 短剧需求。
- `https://www.v2ex.com/t/1241993`：本次直接请求超时，相关线索来自市场研究子角色的公开搜索记录，列为待复核 B 级证据。
- `https://www.v2ex.com/t/1251354`：页面要求登录，未绕过；只使用搜索索引摘要并标为 C 级。

### 结论

- 已确认公开市场存在带预算、明确交付和进行中状态的 AI 视频/短剧剪辑需求。
- 已确认低价整季承制与精品定制并存，不能把行业热度等同于可成交需求。
- 未向任何线索发送消息；未购买、转卖或批量采集联系方式。
- AnySearch 匿名额度耗尽后停止搜索；自动返回的新 API key 未保存到磁盘。

### 文档产物

- `docs/agentops/RESEARCH.md`
- `docs/agentops/LEADS.md`
- `docs/agentops/REQUIREMENTS.md`
## TASK-012 低成本渠道证据（2026-10-26）

- `https://support.upwork.com/hc/en-us/articles/211062898-Connects`：HTTP 200；官方说明 Connects 用于提交 proposal，单价 $0.15，新用户可能在购买或订阅后获得一次性 50 个 Connects，部分用户每月有 10 个免费 Connects。
- `https://www.freelancer.com/feesandcharges/`：HTTP 200；官方说明注册免费，免费会员每月可投 6 次 bid，投标可能要求最低账户余额；项目成交后平台收取费用，固定价和按小时项目约 10% 或最低 $5。
- `https://eleduck.com/`：HTTP 200；公开首页有“机会/项目/招聘/自由职业”入口，使用社区“电量”机制，未见上万元投标会员要求。
- `https://remote-china.com/jobs/2099`、`/2210`、`/2131`：此前公开页可访问，原文需登录后查看；未见大额投标会员门槛。
- `https://www.zbj.com/`：HTTP 200；首页出现“免费开店赚钱”，但具体任务是否收取保证金、服务费或要求会员需逐单核验。
- 结论：一品威客 D001/D002/D003 因 VIP 门槛暂时降级；优先执行 Remote-China、V2EX、电鸭等低成本或免费申请渠道。
- 未注册付费会员、未充值、未发送任何消息。
## D004 原站追溯（2026-10-26）

- Remote-China `https://remote-china.com/jobs/2099` 页面状态 200，公开摘要可见；按钮实际跳转 `https://remote-china.com/login?next=/jobs/2099`。
- Remote-China 积分页 `https://remote-china.com/pricing` 显示：查看职位链接每次消耗 1 积分；50 积分约 0.198 元/积分，200 积分约 0.149 元/积分，400 积分约 0.125 元/积分。最低档约 9.9 元，不是大额 VIP。
- 通过 360 搜索跳转定位原站：`https://www.zhaopin.com/jobdetail/CCL1509883180J40878619811.htm`。
- 智联原职位页当前返回 HTTP 404；搜索结果缓存显示原岗位发布日期为 2025-08-01，岗位为“AI视频制作-居家办公”，薪资 100–200 元/时。
- 结论：Remote-China 的 2026-10-08 是聚合页/转载时间，不能证明岗位当前有效。D004 降为 C 级过期线索，不为该条充值积分。
- 未注册 Remote-China、未充值、未联系发布者。

## TASK-013 《执光》投标文字方案（2026-11-08）

### 附件核对

- 原始压缩包：`C:/Users/陈楷浩/OneDrive/桌面/Downloads/549f9f7f850445c480cf82941b771fdb_20261107134008A814.zip`
- 附件编码异常，按文件类型提取到 `projects/ai_video_bid_20261108/attachments/`；未修改原始压缩包。
- 剧本文件：`file_09.docx`，解析文本见 `projects/ai_video_bid_20261108/file_09_parsed.txt`，正文约10分钟版《执光》，包含10场及补场。
- 结构文件：`file_10.docx`，解析文本见 `projects/ai_video_bid_20261108/file_10_parsed.txt`，标题为《执光》故事大纲·结构表，标注11段、约4分33秒、16:9。
- 视频初稿：`file_01.mp4`，实测1922×1080、60fps、11972帧、199.533秒，含视频和音频轨道。

### 案例证据

- `projects/beijing_age_slice/beijing_age_slice_4s_720p_trial_v3.mp4`：1280×720、16:9、24fps、4.00秒、无音轨；对应运镜与年代转场能力。
- `projects/等雨停_试稿/等雨停_完整10镜头_480p_修正版_final.mp4`：约50.92秒、9:16、480p、10镜头；对应叙事、转场、配音字幕与后期质检能力。
- 不将客户提供的《执光》初稿作为投标自有案例；案例定义以真实项目文件为准。

### 交付与验证

- `projects/ai_video_bid_20261108/执光_投标文字方案_v1.docx`
- `projects/ai_video_bid_20261108/执光_投标文字方案_v1.md`
- `projects/ai_video_bid_20261108/平台填写版_执光_v1.txt`
- `projects/ai_video_bid_20261108/qa_render/执光_投标文字方案_v1.pdf`：6页；页面内容边界在 62.4–549.5pt 范围内；已通过章节存在性检查。
- 未付费生成、未对外发送、未发布、未创建PR。
- `projects/ai_video_bid_20261108/执光_投标发送包_20261108.zip`：17,520,677 bytes，含DOCX、PDF、平台文字、两条案例视频和两张检查图。


## TASK-014 《心光如潮》10秒试稿分析（2026-11-08）

### 输入核对

- 脚本：`C:/Users/陈楷浩/OneDrive/桌面/Downloads/c7b531fc93374aa5bf88ff20e953b5bd_20261105204636A367.txt`；解析出约22个唯一画面、11段旁白，时间标注为0:00–3:35。
- 小说正文：`C:/Users/陈楷浩/OneDrive/桌面/Downloads/3cfc1ea01a9142c19bf220f1237e6332_20261105200810A363.txt`；用于补充人物关系和叙述语气。
- 画面12–14原文：`projects/ai_video_bid_20261108/心光如潮_画面12-14原文.txt`。
- 角色参考图：下载到 `projects/ai_video_bid_20261108/character_refs/`；第一张2848×1600，第二张1536×1536。
- 用户已确认：红框就是两张图的脸部区域；第一张为秦谪，第二张为姜清漓。此前自动红色区域检测未识别到完整矩形框，不影响按脸部区域作为身份锚点。

### 方案产物

- `projects/ai_video_bid_20261108/心光如潮_试稿执行方案_v1.md`：含10秒三段分镜、音频取舍、角色设定卡提示词、三张关键帧提示词、三条图生视频提示词、缺失清单、预算和工期风险。
- `projects/ai_video_bid_20261108/心光如潮_统计.txt`：画面/旁白/章节统计。

### 未执行

- 未调用付费图片/视频API，未生成试片，未发送或发布任何内容。

## TASK-014 费用与参考核对（2026-11-08）

- 官方模型价格页：`https://ark.volcengine.com/region:cn-beijing/docs/model-pricing`；本地抽取：`projects/ai_video_bid_20261108/official_model-pricing.md`。
- Seedream 5.0 Flash：输出 0.12元/张，输入图免费。
- Seedance 2.0 Mini 720p：约0.50元/秒；Seedance 2.0 标准版720p：约0.99元/秒；Seedance 2.5 720p：约1.51元/秒。
- 10秒试片推荐路线：Seedream约6–12张图 + Seedance 2.0标准版20–30秒等效候选，预计31–38元，建议上限50元。
- 外部参考链接打开为淘乎任务页，未取得可播放的《劫缘难避》视频；未据此声称完成镜头拆解。
- 未发起付费生成，等待用户确认预算。

## TASK-014 最终交付（2026-11-08）

### 成片

- `projects/ai_video_bid_20261108/generation/final/心光如潮_10秒试稿_720p.mp4`：5,325,489 bytes。
- 720×1280、24fps、240帧、10.00秒、H.264 High yuv420p、AAC 48kHz立体声。
- 中文字幕、右上角“试稿 · 心光如潮”水印、原创氛围音乐已合成。
- 技术QC：无长黑帧/冻结；音频峰值约 -1.5dB；只有片尾淡出黑帧。

### 选片

- 画面12A：人脸一致性平均 0.885、最低 0.859。
- 画面13A：最高 0.890、平均 0.791。
- 画面14B：最高 0.681、平均 0.631。
- 说明：SFace 对2D漫脸只作相对排序，不等同于客户审美验收。

### 成本

- Seedream 5.0 Flash：8张 ×0.12 = 0.96元。
- Seedance 2.0标准版：6条 ×87,300 tokens = 523,800 tokens；按46元/百万tokens约24.09元。
- API合计约25.05元，低于31–38元区间和50元上限。

### 交付包

- `projects/ai_video_bid_20261108/generation/心光如潮_10秒试稿_交付包_20261108.zip`：41,304,883 bytes，25个文件，含成片、字幕、设定卡、关键帧、选用片段、全部候选、配音、音乐、说明和成本记录。

### 第三方工具

- `imageio-ffmpeg 0.8.1`（BSD-2-Clause）用于本地视频封装。
- OpenCV Zoo YuNet / SFace 模型（Apache-2.0）用于面部一致性质检，不随成片分发。

## TASK-015 FormFunk 18秒广告（2026-11-10）

### 成片

- `projects/formfunk_ad_20261109/generation/final/FormFunk_蓝线生长_18秒品牌广告.mp4`：8,470,617 bytes。
- 720×1280、24fps、432帧、18.00秒、H.264 High yuv420p、AAC 48kHz立体声。
- 英文字幕、英文旁白、原创氛围音乐、FormFunk片尾字标已合成。
- 技术QC：无长黑帧/冻结；第1帧为淡入黑场；音频峰值约-4dB。

### 产品匹配

- 镜1B：SIFT约259（抽检）。
- 镜2A：约135。
- 镜3B：约113。
- 镜4A：约338，作为产品英雄镜头。
- 镜5B：约185。

### 成本

- Seedream 5.0 Flash：10张 ×0.12 = 1.20元。
- Seedance 2.0标准版：10条 ×87,300 tokens = 873,000 tokens；按46元/百万tokens约40.16元。
- 合计约41.36元，低于65元上限。

### 交付包

- `projects/formfunk_ad_20261109/generation/FormFunk_蓝线生长_18秒广告_交付包_20261110.zip`：54,603,923 bytes，35个文件，含成片、字幕、关键帧、选用片段、全部候选、配音、音乐、说明和成本记录。

### 限制

- 两条参考视频未收到，未声称复刻参考片。
- 未收到正式Logo矢量，片尾使用临时文字排版。

## TASK-016 即梦 API 半自动小说推文内容工厂（2026-11-10）

### 环境验证

- `ARK_API_KEY` 已配置。
- `seedream_health_check`：`ok=true`，默认模型 `doubao-seedream-5-0-flash-260915`，模型列表可访问。
- `seedance_health_check`：`ok=true`，默认模型 `doubao-seedance-2-0-mini-260615`，模型列表可访问。
- `PEXELS_API_KEY`、`PIXABAY_API_KEY` 当前未配置；程序会显示待申请并允许手动素材导入。
- 新 MCP 只暴露：`seedream_health_check`、`seedream_generate_image`、`seedance_health_check`、`seedance_create_video_task`、`seedance_get_video_task`、`seedance_wait_and_download`。

### 自动化验证

- `python -m pytest -q`：12 passed。
- 测试覆盖：脚本模板、Pexels/Pixabay 解析、生成成本估算、发布包文件、SRT、API 创建与 dry-run、即梦工具白名单、无 Kling 导入。
- `start.bat`：双击启动成功，首页、静态资源、健康检查、项目列表、线索列表均返回 200。
- FFmpeg 冒烟渲染：1080×1920、30fps、30.00 秒、H.264 + AAC，字幕和封面生成成功。
- 未调用付费图片/视频生成；未对外发布、未上传抖音/小红书、未保存平台 Cookie。

### 产物

- `projects/novel_promo_factory/app/`：FastAPI 本地控制台与业务逻辑。
- `projects/novel_promo_factory/jimeng_mcp/server.py`：即梦-only MCP。
- `projects/novel_promo_factory/tests/`：12 个自动化测试。
- `projects/novel_promo_factory/start.bat`：一键启动。

## TASK-017 小说候选池与自动选书（2026-11-11）

### 已实现

- `novel_candidates` 数据表，字段包括标题、类型、正文、授权状态、标签、优先级、状态和使用次数。
- 手动候选选择：通过“用这条创建项目”生成待审核项目。
- 自动候选选择：按类型、关键词、优先级、使用次数评分。
- 自动创建项目后先生成脚本/分镜，状态为 `pending_approval`，`decision=pending`。
- 用户可接受项目，或拒绝并自动创建下一条候选项目。
- 付费生成门控：`decision=pending` 时拒绝调用 Seedream/Seedance。

### 验证

- `pytest -q`：14 passed。
- API 联调：新增两个候选 -> 自动创建待审项目 -> 拒绝并切换到第二条 -> 接受第二条 -> dry-run 成功。
- 未联网抓取小说平台，未执行付费生成或对外发布。
