# AI 短剧工作台

> 固定三条工作流：每日视频项目 → GitHub 情报 → 豆包制作 Skill。
> 后续在本对话中直接说“做今天的视频项目 / 扫描 GitHub 情报 / 用豆包制作视频”即可。

## 固定入口

- 总览：`http://127.0.0.1:8765/`
- 每日视频项目：`http://127.0.0.1:8765/#daily`
- GitHub 情报：`http://127.0.0.1:8765/#radar`
- 豆包制作 Skill：`http://127.0.0.1:8765/#doubao`

三条工作流的标准口令、目录和风险边界见 `../../docs/agentops/WORKSPACE.md`。

## 这是什么

一个本地 Windows 网页工具，用于：

- 输入小说文本，生成 5 段式推文脚本和分镜
- 从 Pexels / Pixabay 搜索免费视频素材
- 用火山方舟即梦同源 Seedream / Seedance 生成关键图片和短视频
- 用本地 Edge TTS 配音、FFmpeg 合成竖屏视频
- 生成抖音 / 小红书发布包
- 人工发布后记录链接、数据和客户线索

程序**不调用 Kling API**，也不会读取 `KLING_API_KEY`。

## 启动

双击 `start.bat`。首次会自动创建 `.venv` 并安装依赖。

浏览器地址：`http://127.0.0.1:8765`

## 必须配置的环境变量

```text
ARK_API_KEY=你的火山方舟 API Key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL_NAME=doubao-seedream-5-0-flash-260915
SEEDANCE_MODEL_NAME=doubao-seedance-2-0-mini-260615
```

可选免费素材 API：

```text
PEXELS_API_KEY=你的PexelsKey
PIXABAY_API_KEY=你的PixabayKey
```

没有素材 Key 时，仍然可以使用“本地素材文件夹”继续制作。若放入 `assets/manual/bgm.mp3`、`bgm.wav` 或 `bgm.m4a`，渲染时会自动混入低音量背景音乐。

## 可选路径

默认会从以下目录加载现有 MCP 的 Seedream / Seedance 客户端：

`C:\Users\陈楷浩\OneDrive\桌面\脚本数据\kling-image-mcp`

如果路径变化，设置：

```text
JIMENG_MCP_SOURCE_ROOT=新的MCP目录
```

## 使用流程

1. 创建项目，填写标题、类型、自有/已授权文本。
2. 点击“生成脚本和分镜”。
3. 点击“搜索免费素材”；没有 Key 时可把素材放进 `assets/manual/` 后刷新。
4. 点击“估算成本”，确认预计费用。
5. 点击“确认生成”，调用即梦 API。
6. 点击“渲染视频”，生成 9:16 MP4。
7. 点击“生成发布包”，得到抖音/小红书封面、文案和发布清单。
8. 手动上传到官方创作中心，回填发布链接、数据和客户线索。

## 豆包桌面端免费额度流程

网页新增了“豆包免费额度任务桥”，适合不调用付费 API、只使用豆包桌面端每日免费额度的项目。

1. 选择项目，点击“准备豆包 50 秒任务包”。
2. 程序会生成 5 个连续的 10 秒镜头，并把原分镜备份到：
   `content/<项目ID>/doubao_batch/original_before_doubao.json`
3. 在豆包桌面端选择 `Seedance 2.0 Mini`、`自动 · 10s`、`9:16`，逐条粘贴任务包中的提示词。
4. 把生成结果保存为：
   `content/<项目ID>/doubao_batch/segments/shot-01.mp4` 至 `shot-05.mp4`
5. 回到网页点击“导入豆包片段”。
6. 点击“拼接并加音乐”，生成 1080×1920、30fps、H.264 + AAC 的 50 秒成片。

成片和工程文件位于：

- 任务计划：`doubao_batch/plan.json`
- 提示词：`doubao_batch/prompts.md`
- 原始音乐：`bgm.wav`
- 字幕：`doubao_batch/render/subtitles.srt`
- 成片：`doubao_batch/render/last_train_50s_1080x1920.mp4`

豆包官方没有公开精确的视频额度换算。按常见口径保守估算，每天约 10 个额度，10 秒约 2 个额度，即约 50 秒/天。程序只记录估算值，不读取或修改账号额度。

如果生成结果只保存在豆包缓存中，可使用辅助脚本提取最近的 MP4：

```powershell
.\.venv\Scripts\python.exe tools\extract_doubao_cache.py "content\<项目ID>\doubao_batch\segments\shot-01.mp4" --since-minutes 20
```

## 安全边界

- 不保存平台密码或 Cookie
- 不自动登录、自动发布、自动评论或私信
- 所有付费生成都必须由你在控制台点击确认
- 单条视频默认不超过 20 元，每月不超过 600 元
- 没有许可证记录的素材不能进入发布包

## 免费素材来源

- Pexels: https://www.pexels.com/api/
- Pixabay: https://pixabay.com/api/docs/
- Mixkit: https://mixkit.co/license/#videoFree

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 小说候选池与自动选书

当前版本支持两种选书方式：

1. **手动选择**：在“小说候选池”添加候选小说，点击“用这条创建项目”。
2. **自动选择**：填写想要的类型和关键词，点击“自动选一本并创建待审项目”。

自动选择只从你录入的候选池中挑选，不会联网抓取小说平台内容。筛选规则会优先考虑：

- 类型是否匹配
- 标题/标签/正文是否包含关键词
- 候选优先级
- 是否已经使用或拒绝

自动创建的项目会先进入 **待审核** 状态，并生成脚本和分镜，但不会调用付费 API。你可以：

- 点击“接受这个项目”：项目进入可生成状态。
- 点击“拒绝并换一条”：当前候选标记为拒绝，并自动创建下一条候选项目。

只有接受项目后，才能点击“确认即梦生成”。

## 批量推荐项目

网页“小说候选池”现在支持：

- 手动选择单个候选创建项目
- 自动选择单个候选创建项目
- 批量生成 3–5 个待审项目，并自动搜集每个项目的 Pixabay 竖版图片素材

批量项目不会调用付费 Seedream/Seedance；它们会停在“待审核”，你可以在详情里选择接受或拒绝。

当前素材搜索支持 Pixabay 视频和图片。视频下载较慢时，可以先使用图片素材配合 FFmpeg 推拉镜头，再在关键镜头调用即梦生成。


### 免费额度不足时的收尾方式

如果豆包当天额度不足以生成第 5 条镜头，程序允许先导入前 4 条豆包片段，再使用以下工具生成一个 10 秒本地收尾镜头：

```powershell
.\.venv\Scripts\python.exe tools\make_fallback_ending.py
```

该工具会读取 `shot-04.mp4` 的画面和声音，生成带标题排版的 `shot-05.mp4`。这样仍能输出完整 50 秒成片，但第 5 段不是豆包生成。需要纯豆包版本时，应在免费额度恢复后重新生成第 5 段并重渲染。

## AI 短剧情报雷达

网页顶栏新增“AI 情报雷达”。它每 4 小时扫描以下公开来源：

- GitHub 搜索：AI 短剧、AI 漫剧、Seedance/Kling、分镜、角色一致性、ComfyUI 视频工作流
- GitHub 仓库 README / SKILL.md、Star、Fork、最近更新和许可证
- OpenAI News RSS、Kling Release Notes、Runway Changelog、MiniMax News、火山方舟产品页

### 使用方式

1. 双击 `start.bat`，在顶栏切换到“AI 情报雷达”。
2. 点击“立即扫描”建立第一次基线。第一次只看当前热度与相关性，不伪造 Star 增长率。
3. 后续扫描会按 24 小时快照计算 Star 增量，并以 100 分制排序：
   - 相关性 40
   - Star 增长 25
   - 近期活跃 15
   - 可信度 10
   - 降本潜力 10
4. 每项可标记为未读、已收藏、试用中、已试、已忽略。
5. 每次扫描后自动选出 3 项“今日自动精选”，无需逐项挑选。
6. 每项仍可标记为未读、已收藏、试用中、已试、已忽略。
7. 日报保存在 `data/radar/reports/`，也可在网页点击“打开今日日报”。

### 自动精选与自动安装

- 每日最多自动安装 1 个新的 Skill，避免一次引入过多未经实际使用的技能。
- 只处理评分不低于 70、许可证在白名单内、仓库根目录存在 `SKILL.md` 的项目。
- 自动检查文件数量、总体体积、ZIP 路径穿越、符号链接和危险模式。
- 通过检查后从 GitHub 官方归档下载，只复制文件，不执行其中任何脚本。
- 含脚本的 Skill 会加入 `RADAR_INSTALL_NOTICE.md`，提示首次运行前复核依赖和权限。
- 不是标准 Skill 包的工具仍会进入精选和日报，但只提供原链接，不会被误装。
- 自动安装记录保存在 SQLite，并显示在网页“最近自动安装的 Skill”和当日日报中。

当前已自动安装的示例：`A-cat-with-carrots/OnlyShot`，Skill 名 `ai-short-drama`，路径为 `C:\Users\陈楷浩\.codex\skills\ai-short-drama`。

### 后台自动运行

首次需要人工双击一次：

```text
enable_radar_task.bat
```

它会创建 Windows 计划任务 `AI-Drama-Radar`，每天 00:30、04:30、08:30、12:30、16:30、20:30 扫描，因此早上 08:30 会生成当天日报。电脑关机或休眠错过时间后，Windows 会尝试补跑。

取消自动运行：

```text
disable_radar_task.bat
```

### 可选配置

没有 GitHub Token 也能运行，但搜索 API 限额较低。可在启动程序前设置：

```powershell
setx GITHUB_TOKEN "你的只读 GitHub Token"
```

Token 只从环境变量读取，不写入 SQLite 或日志。关闭终端并重新启动应用后生效。

### 边界

- 只读取公开 GitHub 和官方公开页面，不登录、不评论、不发送消息。
- 只对通过静态检查的标准 Skill 自动安装；安装过程不执行仓库脚本。
- 不调用 ARK、Kling、Seedream、Seedance 或其他付费生成 API。
- HTML 官方页面只能检测“页面有变化”，具体内容需要打开原链接复核。
- 评分是规则化筛选，不等于对项目质量、安全性和许可证的最终审查。

## 场景声音引擎（MeloTTS + ACE-Step + Freesound）

网页详情页新增“场景声音引擎”。它不是给整条视频随便配一首音乐，而是给每个镜头分别生成或选择：

- 旁白：MeloTTS，中文/中英混合；不可用时回退 Edge TTS。
- 背景音乐：ACE-Step 1.5，根据镜头标题、画面和声音描述生成；不可用时回退本地合成音乐。
- 环境音/音效：Freesound API，默认只选 `Creative Commons 0`；不可用时回退本地合成环境音。

### 1. 配置

在 [Freesound API 申请页](https://freesound.org/apiv2/apply/) 免费申请 Key，然后复制 `.env.example` 为 `.env` 并填写：

```powershell
Copy-Item .env.example .env
```

```text
FREESOUND_API_KEY=你的免费APIKey
FREESOUND_ALLOW_CC_BY=false
ACE_STEP_URL=http://127.0.0.1:8001
ACE_STEP_API_KEY=
ACE_STEP_MODEL=acestep-v15-turbo
MELOTTS_URL=http://127.0.0.1:8766
MELOTTS_SPEAKER=ZH
PUBLISH_VIDEO_DIR=C:\Users\陈楷浩\OneDrive\桌面\MCP一键操作\projects\抖音发布_成片库
```

`.env` 已被 Git 忽略，不要把 Key 提交到仓库。

### 2. 安装本地声音运行时

电脑需要 `uv`、Git，以及足够的磁盘空间：

```powershell
.\setup_audio_runtime.bat
```

它会安装：

- ACE-Step 1.5：`%USERPROFILE%\.codex\audio_runtime\ACE-Step-1.5`
- MeloTTS：`%USERPROFILE%\.codex\audio_runtime\MeloTTS`
- MeloTTS 使用独立 Python 3.11 环境，并只启用中文/中英混合；安装脚本会应用运行时兼容补丁，避免下载无关语言模型。

ACE-Step 主模型首次下载体积较大；空间不足时可以只保留本地合成回退，不影响网站运行。

### 3. 启动声音服务

```powershell
.\start_audio_services.bat
```

服务地址：

- ACE-Step：`http://127.0.0.1:8001`
- MeloTTS：`http://127.0.0.1:8766`

也可以单独运行 `start_ace_step.bat` 或 `start_melotts.bat`。

### 4. 网页操作

1. 选择项目，先完成画面或豆包镜头导入。
2. 点击“准备场景声音方案”，系统会按每个镜头生成旁白、音乐和音效提示。
3. 点击“生成场景声音素材”，生成音频并写入 `sound/manifest.json`。
4. 点击“生成场景混音成片”，输出替换为场景声音分层的 MP4。
5. 最终 MP4 同时复制到 `PUBLISH_VIDEO_DIR`，默认是 `projects/抖音发布_成片库/`。

声音工程文件位于项目目录：

```text
sound/plan.json
sound/manifest.json
sound/assets/voice/
sound/assets/music/
sound/assets/sfx/
sound/render/
```

### 5. API

```text
GET  /api/projects/{id}/sound/status
POST /api/projects/{id}/sound/plan
POST /api/projects/{id}/sound/generate
POST /api/projects/{id}/sound/render
```

### 6. 授权边界

- Freesound 默认只使用 `CC0`；打开 `FREESOUND_ALLOW_CC_BY=true` 后，会在清单中记录作者和来源，发布时需要按要求署名。
- 不使用 `CC-BY-NC` 音乐或音效制作商业化内容。
- ACE-Step 1.5 为 MIT；生成结果仍应避免刻意模仿受版权保护的歌曲或艺人风格。
- MeloTTS 为 MIT；语音克隆或真人声音样本必须取得明确授权。
- 发布到抖音等平台时，应按平台要求标注 AI 生成内容。
