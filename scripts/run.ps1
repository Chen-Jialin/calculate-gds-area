# Windows launcher / Windows 启动器。Forward arguments literally / 原样转发参数。
$ErrorActionPreference = 'Stop'
$gdsLanguage = $env:GDS_AREA_LANG
if (-not $gdsLanguage) { $gdsLanguage = 'bilingual' }
for ($gdsArgIndex = 0; $gdsArgIndex -lt $args.Count; $gdsArgIndex++) {
    if ($args[$gdsArgIndex] -eq '--lang' -and $gdsArgIndex + 1 -lt $args.Count) {
        $gdsLanguage = $args[$gdsArgIndex + 1]
    } elseif ($args[$gdsArgIndex] -like '--lang=*') {
        $gdsLanguage = $args[$gdsArgIndex].Substring(7)
    }
}
function Get-GdsMessage([string]$English, [string]$Chinese) {
    if ($gdsLanguage -eq 'en') { return $English }
    if ($gdsLanguage -eq 'zh') { return $Chinese }
    return $Chinese + ' / ' + $English
}
$gdsSavedConsoleEncoding = [Console]::OutputEncoding
try {
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ($gdsLanguage -notin @('en', 'zh', 'bilingual')) {
    [Console]::Error.WriteLine('无效语言；请选择 en、zh 或 bilingual。 / Invalid language; choose en, zh or bilingual.')
    exit 2
}
$entrypoint = 'gds_area.py'
if ($env:GDS_AREA_ENTRYPOINT -eq 'self_test.py') { $entrypoint = 'self_test.py' }
$scriptFile = Join-Path $PSScriptRoot $entrypoint
$check = 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,15) else 1)'
if ($env:GDS_AREA_MANAGED_PYTHON -ne '1') {
    foreach ($candidate in @('python', 'python3', 'py')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') {
            $prefix = @()
            if ($candidate -eq 'py') { $prefix = @('-3') }
            & $command.Source @prefix -c $check 2>$null
            if ($LASTEXITCODE -eq 0) {
                & $command.Source @prefix -X utf8 $scriptFile @args
                exit $LASTEXITCODE
            }
        }
    }
}
$cacheDir = $env:GDS_AREA_CACHE
if (-not $cacheDir) { $cacheDir = Join-Path $env:LOCALAPPDATA 'gds-area' }
$cacheDir = [System.IO.Path]::GetFullPath($cacheDir)
New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
$uvExe = Join-Path $cacheDir 'uv\uv.exe'
if ($uvCommand) { $uvExe = $uvCommand.Source }
if (-not (Test-Path -LiteralPath $uvExe)) {
    [Console]::Error.WriteLine((Get-GdsMessage 'Downloading uv from astral.sh to install an isolated Python runtime...' '正在从 astral.sh 下载 uv，以安装隔离的 Python 运行环境……'))
    $installer = Join-Path $cacheDir 'uv-install.ps1'
    Invoke-WebRequest -Uri 'https://astral.sh/uv/install.ps1' -OutFile $installer -UseBasicParsing
    $savedInstallDir = $env:UV_INSTALL_DIR
    $savedNoPath = $env:UV_NO_MODIFY_PATH
    try {
        $env:UV_INSTALL_DIR = Join-Path $cacheDir 'uv'
        $env:UV_NO_MODIFY_PATH = '1'
        & $installer | ForEach-Object { [Console]::Error.WriteLine($_) }
        if (-not (Test-Path -LiteralPath $uvExe)) { throw (Get-GdsMessage 'uv installation failed.' 'uv 安装失败。') }
    } finally {
        $env:UV_INSTALL_DIR = $savedInstallDir
        $env:UV_NO_MODIFY_PATH = $savedNoPath
    }
}
$env:UV_PYTHON_INSTALL_DIR = Join-Path $cacheDir 'python'
$env:UV_CACHE_DIR = Join-Path $cacheDir 'uv-cache'
$pythonSelection = @('--managed-python', '--python', '3.12')
if ($env:GDS_AREA_UV_PYTHON) { $pythonSelection = @('--python', $env:GDS_AREA_UV_PYTHON) }
& $uvExe run --no-project @pythonSelection --default-index 'https://pypi.org/simple' --with 'klayout==0.30.12' -- python -X utf8 $scriptFile @args
exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine((Get-GdsMessage 'Operation failed; original diagnostic: ' '操作失败；原始诊断信息：') + $_.Exception.Message)
    exit 2
} finally {
    [Console]::OutputEncoding = $gdsSavedConsoleEncoding
}
