$ErrorActionPreference = 'Stop'
$Apps = $PSScriptRoot
$RunDir = Join-Path $Apps 'run'

foreach ($name in @('huobao', 'openmontage', 'awesome-skills')) {
    $pidFile = Join-Path $RunDir "$name.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $processId = [int](Get-Content -LiteralPath $pidFile)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($process) {
        $commandLine = [string]$process.CommandLine
        if (-not $commandLine.Contains($Apps, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Warning "跳过 PID $processId：命令行不属于当前部署目录。"
            continue
        }
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "[STOP] $name (PID $processId)"
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host '三个本机服务已停止。'
