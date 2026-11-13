param()
$ErrorActionPreference = 'Stop'
$taskName = 'AI-Drama-Radar'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "计划任务 $taskName 不存在，无需删除。"
    exit 0
}
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "已删除计划任务：$taskName"
