# DevMind Web Installer (Windows)
# Run: iwr -useb https://aarav7162.github.io/dev-devmind/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  DevMind Installer" -ForegroundColor Cyan
Write-Host "  ------------------" -ForegroundColor DarkGray
Write-Host ""

$BASE_URL = "https://aarav7162.github.io/dev-devmind/"
$INSTALL_DIR = "$env:USERPROFILE\.devmind\bin"
$BIN_NAME = "devmind.exe"

# 1. Create install directory
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
}

# 2. Get the binary (with local/offline testing fallback)
Write-Host "  [1/3] Getting devmind.exe..." -NoNewline

# Determine if we have a local build available (for developer/offline installation)
$LOCAL_BIN = ""
$POSSIBLE_PATHS = @(
    (Join-Path $PSScriptRoot "devmind.exe"),
    (Join-Path $PSScriptRoot "release\devmind.exe"),
    (Join-Path $PSScriptRoot "..\release\devmind.exe"),
    (Join-Path (Get-Location) "release\devmind.exe"),
    (Join-Path (Get-Location) "devmind.exe")
)

foreach ($path in $POSSIBLE_PATHS) {
    if (Test-Path $path) {
        $LOCAL_BIN = $path
        break
    }
}

if (![string]::IsNullOrWhiteSpace($LOCAL_BIN)) {
    # Local developer/testing mode - copy the binary directly
    try {
        Copy-Item -Path $LOCAL_BIN -Destination "$INSTALL_DIR\$BIN_NAME" -Force
        Write-Host " [OK] (Installed from local build)" -ForegroundColor Green
    } catch {
        Write-Host " [FAILED] (Local copy failed)" -ForegroundColor Red
        Write-Host " Attempting web download..."
        $LOCAL_BIN = ""
    }
} else {
    # Web downloader mode - fetch from GitHub Pages URL
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "$($BASE_URL)$($BIN_NAME)" -OutFile "$INSTALL_DIR\$BIN_NAME" -UseBasicParsing
        Write-Host " [OK] (Downloaded from Web)" -ForegroundColor Green
    } catch {
        Write-Host " [FAILED]" -ForegroundColor Red
        Write-Host ""
        Write-Host "Error: Could not retrieve devmind.exe." -ForegroundColor Red
        Write-Host "  Online Download Failed: The repository is not yet published to GitHub Pages at: $($BASE_URL)" -ForegroundColor Yellow
        Write-Host "  Offline Fallback Failed: No local 'devmind.exe' was found in the current directory." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To install your local build:" -ForegroundColor White
        Write-Host "  1. Open PowerShell inside the FocusFlow project directory." -ForegroundColor DarkGray
        Write-Host "  2. Run: .\release\install.ps1" -ForegroundColor Cyan
        Write-Host ""
        exit 1
    }
}

# 3. Configure PATH
Write-Host "  [2/3] Configuring system PATH..." -NoNewline
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$INSTALL_DIR*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$INSTALL_DIR", "User")
    Write-Host " [OK] Added to PATH" -ForegroundColor Green
} else {
    Write-Host " [OK] Already in PATH" -ForegroundColor DarkGray
}

# 4. Optional Configurations (calming ocean sound setup)
Write-Host "  [3/3] Setting up audio preferences..."
Write-Host ""
$choice = Read-Host "        Would you like to enable calming ocean sounds during deep work? (Y/N) [Default: Y]"
$soundEnabled = $true
if ($choice -eq "N" -or $choice -eq "n" -or $choice -eq "no" -or $choice -eq "NO") {
    $soundEnabled = $false
    Write-Host "        [OK] Ocean sounds disabled by default." -ForegroundColor DarkGray
} else {
    Write-Host "        [OK] Ocean sounds enabled by default." -ForegroundColor Green
}

$CONFIG_DIR = "$env:USERPROFILE\.devmind"
$CONFIG_PATH = "$CONFIG_DIR\focus_config.json"
if (-not (Test-Path $CONFIG_DIR)) {
    New-Item -ItemType Directory -Force -Path $CONFIG_DIR | Out-Null
}

if (Test-Path $CONFIG_PATH) {
    try {
        $existing = Get-Content -Raw $CONFIG_PATH | ConvertFrom-Json
        $existing | Add-Member -NotePropertyName "sound_enabled" -NotePropertyValue $soundEnabled -Force
        $existing | ConvertTo-Json | Out-File -FilePath $CONFIG_PATH -Encoding utf8
    } catch {
        $config = @{ "sound_enabled" = $soundEnabled }
        $config | ConvertTo-Json | Out-File -FilePath $CONFIG_PATH -Encoding utf8
    }
} else {
    $config = @{ "sound_enabled" = $soundEnabled }
    $config | ConvertTo-Json | Out-File -FilePath $CONFIG_PATH -Encoding utf8
}

Write-Host ""
Write-Host "  🚀 Installation Successful!" -ForegroundColor Green
Write-Host ""
Write-Host "  To finish setup:" -ForegroundColor White
Write-Host "    1. Restart your terminal (important!)" -ForegroundColor DarkGray
Write-Host "    2. Go to any project folder" -ForegroundColor DarkGray
Write-Host "    3. Run: devmind start" -ForegroundColor Cyan
Write-Host ""
