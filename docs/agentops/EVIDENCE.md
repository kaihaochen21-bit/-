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
