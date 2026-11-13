param(
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$Message
)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = $Title
$notify.BalloonTipText = $Message
$notify.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$notify.Visible = $true
$notify.ShowBalloonTip(6000)
Start-Sleep -Seconds 7
$notify.Dispose()
