# 即梦 API 半自动小说推文内容工厂

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
