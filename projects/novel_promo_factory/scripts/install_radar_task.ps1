param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw '找不到 .venv Python。请先双击 start.bat 完成依赖安装。'
}
$execute = if (Test-Path -LiteralPath $pythonw) { $pythonw } else { $python }
$taskName = 'AI-Drama-Radar'
$action = New-ScheduledTaskAction -Execute $execute -Argument '-m app.radar_cli scan --scheduled' -WorkingDirectory $root
$hours = @(0, 4, 8, 12, 16, 20)
$triggers = foreach ($hour in $hours) {
    $at = (Get-Date).Date.AddHours($hour).AddMinutes(30)
    New-ScheduledTaskTrigger -Daily -At $at
}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings -Description 'AI 短剧情报雷达：每 4 小时扫描 GitHub 与官方动态' -Force | Out-Null
Write-Host "已安装计划任务：$taskName"
Write-Host "运行时间：每天 00:30、04:30、08:30、12:30、16:30、20:30"
Write-Host "如错过运行时间，Windows 会在恢复后补跑。"
