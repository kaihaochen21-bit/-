[CmdletBinding()]
param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Apps = $Root
$RunDir = Join-Path $Apps 'run'
$NodeDir = Join-Path $Apps '.tools\node-v24.22.1-win-x64'
$NodeExe = Join-Path $NodeDir 'node.exe'
$VenvPython = Join-Path $Apps '.venvs\openmontage\Scripts\python.exe'
$SystemPython = (Get-Command python -ErrorAction Stop).Source
$HuobaoDir = Join-Path $Apps 'huobao-drama-ai'
$OpenMontageDir = Join-Path $Apps 'openmontage'
$AwesomeDir = Join-Path $Apps 'awesome-short-drama-skills'

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

function Test-Listening([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Start-HiddenService([string]$Name, [string]$FilePath, [string[]]$ArgumentList, [string]$WorkingDirectory) {
    $out = Join-Path $RunDir "$Name.out.log"
    $err = Join-Path $RunDir "$Name.err.log"
    $process = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    Set-Content -LiteralPath (Join-Path $RunDir "$Name.pid") -Value $process.Id
    return $process
}

function Wait-Http([string]$Url, [int]$TimeoutSeconds = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -MaximumRedirection 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 750
    }
    return $false
}

foreach ($name in @(
    'ARK_API_KEY','VOLCENGINE_API_KEY','OPENAI_API_KEY','DEEPSEEK_API_KEY',
    'GEMINI_API_KEY','GOOGLE_API_KEY','KLING_API_KEY','MINIMAX_API_KEY',
    'NVIDIA_API_KEY','NVIDIA_NIM_API_KEY','HF_TOKEN','FAL_KEY',
    'REPLICATE_API_TOKEN','HEYGEN_API_KEY','PEXELS_API_KEY','PIXABAY_API_KEY',
    'ELEVENLABS_API_KEY'
)) {
    Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
}

if (-not (Test-Listening 3001)) {
    if (-not (Test-Path -LiteralPath $NodeExe)) { throw "缺少本地 Node 运行时：$NodeExe" }
    $next = Join-Path $HuobaoDir 'node_modules\next\dist\bin\next'
    if (-not (Test-Path -LiteralPath $next)) { throw 'Huobao Drama AI 尚未安装依赖。' }
    $env:NODE_ENV = 'production'
    $nextArgs = @($next, 'start', '-H', '127.0.0.1', '-p', '3001')
    Start-HiddenService 'huobao' $NodeExe $nextArgs $HuobaoDir | Out-Null
}

if (-not (Test-Listening 8787)) {
    if (-not (Test-Path -LiteralPath $VenvPython)) { throw "缺少 OpenMontage Python 环境：$VenvPython" }
    $secretFile = Join-Path $RunDir 'openmontage.demo.secret'
    if (-not (Test-Path -LiteralPath $secretFile)) {
        [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)) | Set-Content -LiteralPath $secretFile
    }
    $env:OPENMONTAGE_ROOT = $OpenMontageDir
    $env:PROJECTS_ROOT = Join-Path $OpenMontageDir 'projects-local'
    $env:STUDIO_DIST = Join-Path $OpenMontageDir 'studio\dist'
    $env:HOST = '127.0.0.1'
    $env:PORT = '8787'
    $env:STUDIO_PUBLIC_URL = 'http://127.0.0.1:8787'
    $env:STUDIO_CORS_ORIGINS = 'http://127.0.0.1:8787'
    $env:STUDIO_AUTH_REQUIRED = 'true'
    $env:STUDIO_DEMO_ENABLED = 'true'
    $env:STUDIO_DEMO_AUTO_ENTER = 'false'
    $env:STUDIO_GOOGLE_ENABLED = 'false'
    $env:STUDIO_REQUIRE_GITHUB_STAR = '0'
    $env:STUDIO_DEMO_SECRET = (Get-Content -Raw -LiteralPath $secretFile).Trim()
    $env:DATABASE_URL = ''
    $env:STUDIO_DATABASE_URL = ''
    $env:REDIS_URL = ''
    $env:MINIO_ENDPOINT = ''
    Start-HiddenService 'openmontage' $VenvPython @('studio\server\app.py') $OpenMontageDir | Out-Null
}

if (-not (Test-Listening 3002)) {
    $awesomeDist = Join-Path $AwesomeDir 'web\dist'
    if (-not (Test-Path -LiteralPath $awesomeDist)) { throw 'Awesome Short Drama Skills 尚未生成静态站。' }
    $awesomeArgs = @('-m', 'http.server', '3002', '--bind', '127.0.0.1', '--directory', $awesomeDist)
    Start-HiddenService 'awesome-skills' $SystemPython $awesomeArgs $Root | Out-Null
}

$checks = @(
    @{ Name = 'Huobao Drama AI'; Url = 'http://127.0.0.1:3001/api/health'; Entry = 'http://127.0.0.1:3001/' },
    @{ Name = 'OpenMontage Drama Studio'; Url = 'http://127.0.0.1:8787/api/health'; Entry = 'http://127.0.0.1:8787/' },
    @{ Name = 'Awesome Short Drama Skills'; Url = 'http://127.0.0.1:3002/'; Entry = 'http://127.0.0.1:3002/' }
)

$ok = $true
foreach ($check in $checks) {
    if (Wait-Http $check.Url 90) {
        Write-Host "[OK]   $($check.Name)  $($check.Entry)" -ForegroundColor Green
    } else {
        $ok = $false
        Write-Host "[FAIL] $($check.Name)  $($check.Entry)" -ForegroundColor Red
    }
}

if ($OpenBrowser) {
    foreach ($check in $checks) { Start-Process $check.Entry | Out-Null }
}

if (-not $ok) { exit 1 }
