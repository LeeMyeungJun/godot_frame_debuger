param([string]$CapturePath, [switch]$NoOpen)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputRoot = Join-Path $root 'output'
$captureDir = Join-Path $outputRoot 'captures'
$qrenderdoc = Join-Path $root 'RenderDoc\PFiles\RenderDoc\qrenderdoc.exe'
$renderdoccmd = Join-Path $root 'RenderDoc\PFiles\RenderDoc\renderdoccmd.exe'
$exportScript = Join-Path $root 'export_capture.py'
$templatePath = Join-Path $root 'frame_viewer_template.html'
$cacheRoot = Join-Path $outputRoot 'viewer_cache'
foreach ($required in @($qrenderdoc, $renderdoccmd, $exportScript, $templatePath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        [System.Windows.Forms.MessageBox]::Show("필요한 파일을 찾을 수 없습니다.`r`n$required", 'FrameDebugger', 'OK', 'Error') | Out-Null
        exit 1
    }
}
if ([string]::IsNullOrWhiteSpace($CapturePath) -or -not (Test-Path -LiteralPath $CapturePath -PathType Leaf)) {
    $dialog = [System.Windows.Forms.OpenFileDialog]::new()
    $dialog.Title = '분석할 RenderDoc 캡처 선택'
    $dialog.Filter = 'RenderDoc 캡처 (*.rdc)|*.rdc|모든 파일 (*.*)|*.*'
    $dialog.InitialDirectory = if (Test-Path -LiteralPath $captureDir) { $captureDir } else { $root }
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $CapturePath = $dialog.FileName
}
$CapturePath = [System.IO.Path]::GetFullPath($CapturePath)
$capture = Get-Item -LiteralPath $CapturePath
$sha = [System.Security.Cryptography.SHA256]::Create()
$key = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($capture.FullName))).Replace('-', '').Substring(0,16))
$sha.Dispose()
$cacheDir = Join-Path $cacheRoot $key
$textureDir = Join-Path $cacheDir 'textures'
$jsonPath = Join-Path $cacheDir 'frame_data.json'
$assetDirName = $capture.BaseName + '_assets'
$resultDir = Join-Path (Join-Path $outputRoot 'results') $key
$assetDir = Join-Path $resultDir $assetDirName
$assetTextureDir = Join-Path $assetDir 'textures'
$htmlPath = Join-Path $resultDir ($capture.BaseName + '.html')
$statusPath = Join-Path $cacheDir 'status.txt'
$manifestPath = Join-Path $cacheDir 'manifest.json'
$null = New-Item -ItemType Directory -Path $textureDir -Force
$manifest = $null
if (Test-Path -LiteralPath $manifestPath) { try { $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json } catch {} }
$exportHash = (Get-FileHash -LiteralPath $exportScript -Algorithm SHA256).Hash
$cacheValid = $manifest -and $manifest.PSObject.Properties['exportHash'] -and $manifest.exportHash -eq $exportHash -and $manifest.path -eq $capture.FullName -and [long]$manifest.length -eq $capture.Length -and [long]$manifest.ticks -eq $capture.LastWriteTimeUtc.Ticks -and (Test-Path -LiteralPath $jsonPath) -and (Test-Path -LiteralPath (Join-Path $cacheDir 'frames'))

if (-not $cacheValid) {
    Remove-Item -LiteralPath $statusPath -Force -ErrorAction SilentlyContinue
    $env:FRAMEDEBUGGER_CAPTURE = $capture.FullName
    $env:FRAMEDEBUGGER_OUTPUT = $jsonPath
    $env:FRAMEDEBUGGER_TEXTURES = $textureDir
    $env:FRAMEDEBUGGER_STATUS = $statusPath
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $qrenderdoc
    $startInfo.Arguments = '--python "' + $exportScript + '"'
    $startInfo.WorkingDirectory = $root
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $process = [System.Diagnostics.Process]::Start($startInfo)

    $progress = [System.Windows.Forms.Form]::new()
    $progress.Text = 'FrameDebugger'
    $progress.StartPosition = 'CenterScreen'
    $progress.FormBorderStyle = 'FixedDialog'
    $progress.ControlBox = $false
    $progress.Width = 440; $progress.Height = 120
    $label = [System.Windows.Forms.Label]::new()
    $label.Text = 'Draw별 누적 화면과 사용 텍스처를 추출하고 있습니다...'
    $label.AutoSize = $true; $label.Left = 18; $label.Top = 18
    $progress.Controls.Add($label)
    $bar = [System.Windows.Forms.ProgressBar]::new()
    $bar.Style = 'Marquee'; $bar.MarqueeAnimationSpeed = 25
    $bar.Left = 18; $bar.Top = 50; $bar.Width = 388
    $progress.Controls.Add($bar)
    $progress.Show(); $progress.Refresh()
    while (-not $process.HasExited) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 100
    }
    $progress.Close(); $progress.Dispose(); $process.Dispose()
    Remove-Item Env:\FRAMEDEBUGGER_CAPTURE,Env:\FRAMEDEBUGGER_OUTPUT,Env:\FRAMEDEBUGGER_TEXTURES,Env:\FRAMEDEBUGGER_STATUS -ErrorAction SilentlyContinue
    if (-not (Test-Path -LiteralPath $statusPath) -or (Get-Content -Raw -LiteralPath $statusPath) -ne 'ok') {
        $detail = if (Test-Path -LiteralPath $statusPath) { Get-Content -Raw -LiteralPath $statusPath } else { 'RenderDoc 추출기가 결과를 만들지 못했습니다.' }
        [System.Windows.Forms.MessageBox]::Show("캡처 분석에 실패했습니다.`r`n`r`n$detail", 'FrameDebugger', 'OK', 'Error') | Out-Null
        exit 1
    }
    $manifest = [ordered]@{ path=$capture.FullName; length=[long]$capture.Length; ticks=[long]$capture.LastWriteTimeUtc.Ticks; exportHash=$exportHash }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

$data = Get-Content -Raw -LiteralPath $jsonPath
$data = $data.Replace('</', '<\/')
$template = Get-Content -Raw -LiteralPath $templatePath
$null = New-Item -ItemType Directory -Path $assetTextureDir -Force
Copy-Item -Path (Join-Path $textureDir '*') -Destination $assetTextureDir -Force
Copy-Item -LiteralPath (Join-Path $cacheDir 'frames') -Destination $assetDir -Recurse -Force
$assetPrefix = ($assetDirName + '/') | ConvertTo-Json -Compress
$html = $template.Replace('__FRAME_DATA__', $data).Replace('__ASSET_PREFIX__', $assetPrefix)
[System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.UTF8Encoding]::new($false))
Remove-Item -LiteralPath (Join-Path $cacheDir 'index.html') -Force -ErrorAction SilentlyContinue
if (-not $NoOpen) { Start-Process -FilePath $htmlPath }
Write-Output $htmlPath
