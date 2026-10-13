[CmdletBinding()]
param(
    [ValidateSet('Start', 'New', 'Init', 'Status', 'Verify')]
    [string]$Mode = 'Start',

    [string]$ProjectPath = (Get-Location).Path,
    [string]$Goal,
    [string]$ProjectName
)

$ErrorActionPreference = 'Stop'
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$TemplateRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $ScriptRoot))

function Read-Value {
    param([string]$Prompt, [string]$Current)
    if (-not [string]::IsNullOrWhiteSpace($Current)) { return $Current.Trim() }
    return (Read-Host $Prompt).Trim()
}

function Get-PythonCommand {
    foreach ($candidate in @('python', 'python3', 'py')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            $argumentList = @()
            if ($candidate -eq 'py') { $argumentList = @('-3') }
            return [pscustomobject]@{
                File = $command.Source
                Arguments = $argumentList
            }
        }
    }
    return $null
}

function Invoke-AgentOpsVerify {
    $validator = Join-Path $TemplateRoot 'scripts\validate_agentops.py'
    if (-not (Test-Path -LiteralPath $validator)) {
        throw "缺少验证脚本：$validator"
    }

    $python = Get-PythonCommand
    if ($null -eq $python) {
        throw '未找到 Python。请安装 Python 3.11+ 后重新运行验证。'
    }

    $arguments = @($python.Arguments) + @($validator)
    & $python.File @arguments
    if ($LASTEXITCODE -ne 0) { throw 'AgentOps 模板验证失败。' }
}

function Copy-TemplateItem {
    param([string]$Name, [string]$Destination)
    $source = Join-Path $TemplateRoot $Name
    if (-not (Test-Path -LiteralPath $source)) { throw "模板缺少：$Name" }
    $target = Join-Path $Destination $Name
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
}

function Replace-DocPlaceholders {
    param([string]$Destination, [string]$FinalGoal, [string]$Name)
    $projectDoc = Join-Path $Destination 'docs\agentops\PROJECT.md'
    if (Test-Path -LiteralPath $projectDoc) {
        $content = Get-Content -LiteralPath $projectDoc -Raw
        $content = $content.Replace('{{FINAL_GOAL}}', $FinalGoal)
        $content = $content.Replace('{{PROJECT_TYPE}}', '待主智能体根据目标判断')
        $content = $content.Replace('{{AUDIENCE_AND_SCENARIOS}}', '待市场与需求智能体填写')
        [System.IO.File]::WriteAllText($projectDoc, $content, (New-Object System.Text.UTF8Encoding($false)))
    }

    $readme = @"
# $Name

> 最终目标：$FinalGoal

本目录由 AgentOps 模板初始化。请在 Codex 中运行：

```text
`$agentops 继续完成当前项目
```

主智能体会读取 `AGENTS.md` 与 `docs/agentops/`，按市场、需求、架构、编码、测试和主控汇总流程推进。
"@
    [System.IO.File]::WriteAllText((Join-Path $Destination 'README.md'), $readme, (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-AgentOpsInit {
    $resolved = [System.IO.Path]::GetFullPath($ProjectPath)
    $templatePrefix = $TemplateRoot.TrimEnd('\') + '\'
    if ($resolved -eq $TemplateRoot -or $resolved.StartsWith($templatePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw '新项目目录不能位于模板目录内部。请选择独立目录。'
    }

    $finalGoal = Read-Value -Prompt '请输入项目的最终目标' -Current $Goal
    if ([string]::IsNullOrWhiteSpace($finalGoal)) { throw '最终目标不能为空。' }
    $name = if ([string]::IsNullOrWhiteSpace($ProjectName)) { Split-Path -Leaf $resolved } else { $ProjectName.Trim() }

    if (Test-Path -LiteralPath $resolved) {
        $existing = Get-ChildItem -LiteralPath $resolved -Force
        if ($existing.Count -gt 0) { throw "目标目录不是空目录：$resolved" }
    } else {
        New-Item -ItemType Directory -Path $resolved -Force | Out-Null
    }

    foreach ($item in @('.agents', '.codex', '.github', 'docs', 'scripts', 'AGENTS.md', '.gitignore', 'start-agentops.cmd', 'new-agentops-project.cmd')) {
        Copy-TemplateItem -Name $item -Destination $resolved
    }
    Replace-DocPlaceholders -Destination $resolved -FinalGoal $finalGoal -Name $name

    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($null -ne $git -and -not (Test-Path -LiteralPath (Join-Path $resolved '.git'))) {
        & $git.Source -C $resolved init -b main | Out-Host
    }

    $globalName = (& git config --global user.name) 2>$null
    $globalEmail = (& git config --global user.email) 2>$null
    if ($null -ne $git -and -not [string]::IsNullOrWhiteSpace($globalName) -and -not [string]::IsNullOrWhiteSpace($globalEmail)) {
        & $git.Source -C $resolved add .
        & $git.Source -C $resolved commit -m 'chore: initialize agentops project' | Out-Host
    } else {
        Write-Warning '未检测到全局 Git 用户信息，已跳过初始提交。请先配置 user.name 和 user.email。'
    }

    Write-Host "项目已初始化：$resolved" -ForegroundColor Green
}

function Invoke-AgentOpsStart {
    $resolved = [System.IO.Path]::GetFullPath($ProjectPath)
    if (-not (Test-Path -LiteralPath (Join-Path $resolved 'AGENTS.md'))) { throw "不是 AgentOps 项目：$resolved" }
    $finalGoal = Read-Value -Prompt '请输入本轮最终目标；直接回车则继续当前 STATE.md' -Current $Goal
    $goalText = if ([string]::IsNullOrWhiteSpace($finalGoal)) { '继续完成当前项目，读取 STATE.md 的下一步。' } else { $finalGoal }

    $prompt = @"
使用 `$agentops 执行项目目标：
$goalText

要求：
- 先读取 AGENTS.md 和 docs/agentops/ 下的全部必要文档。
- 判断需要哪些能力，并固定调度 market-manager、requirements-analyst、architect、coder、tester。
- 使用功能分支、worktree 和 PR；不要直接修改 main，不要自动合并。
- 更新 TASKS.md、STATE.md、DECISIONS.md、EVIDENCE.md。
- 最后汇总完整交付物、运行方法、测试证据、风险和未完成事项。
"@

    $codex = Get-Command codex -ErrorAction SilentlyContinue
    if ($null -eq $codex) { throw '未找到 codex 命令。请先安装或启动 Codex CLI。' }
    & $codex.Source -C $resolved $prompt
    if ($LASTEXITCODE -ne 0) { throw "Codex 运行失败，退出码：$LASTEXITCODE" }
}

function Invoke-AgentOpsStatus {
    $state = Join-Path $ProjectPath 'docs\agentops\STATE.md'
    $tasks = Join-Path $ProjectPath 'docs\agentops\TASKS.md'
    if (Test-Path -LiteralPath $state) { Write-Host '=== STATE.md ===' -ForegroundColor Cyan; Get-Content -LiteralPath $state }
    if (Test-Path -LiteralPath $tasks) { Write-Host '=== TASKS.md ===' -ForegroundColor Cyan; Get-Content -LiteralPath $tasks }
    if (-not (Test-Path -LiteralPath $state) -and -not (Test-Path -LiteralPath $tasks)) { throw "未找到项目状态：$ProjectPath" }
}

switch ($Mode) {
    'Verify' { Invoke-AgentOpsVerify }
    'Init'   { Invoke-AgentOpsInit }
    'New'    { Invoke-AgentOpsInit; Invoke-AgentOpsStart }
    'Status' { Invoke-AgentOpsStatus }
    'Start'  { Invoke-AgentOpsStart }
}