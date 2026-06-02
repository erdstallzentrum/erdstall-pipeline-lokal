$ErrorActionPreference = "Stop"

Write-Host "Starting Erdstall Admin GUI setup..." -ForegroundColor Cyan

# Go to the folder where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Project folder: $ScriptDir"

function Test-Command {
    param (
        [string]$Command
    )

    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Install-WingetPackage {
    param (
        [string]$Id,
        [string]$Name
    )

    Write-Host "Installing $Name with winget..." -ForegroundColor Yellow

    winget install `
        --id $Id `
        --exact `
        --silent `
        --accept-source-agreements `
        --accept-package-agreements

    Refresh-Path
}

# ------------------------------------------------------------
# 1. Check winget
# ------------------------------------------------------------
if (-not (Test-Command "winget")) {
    Write-Host "ERROR: winget is not installed or not available in PATH." -ForegroundColor Red
    Write-Host "Install 'App Installer' from the Microsoft Store, then run this script again."
    exit 1
}

Write-Host "winget found."

# ------------------------------------------------------------
# 2. Install Python 3.11 if missing
# ------------------------------------------------------------
$Python311Available = $false

if (Test-Command "py") {
    try {
        py -3.11 --version | Out-Null
        $Python311Available = $true
    } catch {
        $Python311Available = $false
    }
}

if ($Python311Available) {
    Write-Host "Python 3.11 already installed. Skipping."
} else {
    Install-WingetPackage -Id "Python.Python.3.11" -Name "Python 3.11"
}

# ------------------------------------------------------------
# 3. Install OpenJDK 17 if missing
# ------------------------------------------------------------
$Java17Available = $false

if (Test-Command "java") {
    try {
        $javaVersionOutput = java -version 2>&1 | Out-String
        if ($javaVersionOutput -match 'version "17\.') {
            $Java17Available = $true
        }
    } catch {
        $Java17Available = $false
    }
}

if ($Java17Available) {
    Write-Host "OpenJDK 17 already installed. Skipping."
} else {
    Install-WingetPackage -Id "Microsoft.OpenJDK.17" -Name "Microsoft OpenJDK 17"
}

# Refresh PATH after Java install
Refresh-Path

# Optional: set JAVA_HOME for this script/session
$PossibleJavaHomes = @(
    "C:\Program Files\Microsoft\jdk-17*",
    "C:\Program Files\Eclipse Adoptium\jdk-17*"
)

foreach ($path in $PossibleJavaHomes) {
    $found = Get-ChildItem $path -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if ($found) {
        $env:JAVA_HOME = $found.FullName
        $env:Path = "$env:JAVA_HOME\bin;$env:Path"
        break
    }
}

if (Test-Command "java") {
    Write-Host "Using Java:"
    java -version
} else {
    Write-Host "WARNING: Java was installed but java is not available in this PowerShell session." -ForegroundColor Yellow
    Write-Host "Close PowerShell, reopen it, and run this script again."
}

# ------------------------------------------------------------
# 4. Install Node.js LTS if missing
# ------------------------------------------------------------
if (Test-Command "node") {
    Write-Host "Node.js already installed. Skipping."
} else {
    Install-WingetPackage -Id "OpenJS.NodeJS.LTS" -Name "Node.js LTS"
}

Refresh-Path

if (Test-Command "node") {
    Write-Host "Using Node: $(node --version)"
}

if (Test-Command "npm") {
    Write-Host "Using npm: $(npm --version)"
}

# ------------------------------------------------------------
# 5. Run npm install if package.json exists
# ------------------------------------------------------------
if (Test-Path "package.json") {
    Write-Host "package.json found. Running npm install..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "No package.json found in project root. Skipping npm install."
}

# ------------------------------------------------------------
# 6. Find Python 3.11 executable
# ------------------------------------------------------------
$PythonCmd = $null

if (Test-Command "py") {
    try {
        py -3.11 -c "import sys; print(sys.executable)" | Out-Null
        $PythonCmd = "py -3.11"
    } catch {
        $PythonCmd = $null
    }
}

if (-not $PythonCmd) {
    Write-Host "ERROR: Python 3.11 could not be found after installation." -ForegroundColor Red
    Write-Host "Close PowerShell, reopen it, and run this script again."
    exit 1
}

Write-Host "Using Python 3.11."

# ------------------------------------------------------------
# 7. Create / use Python virtual environment
# ------------------------------------------------------------
if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists. Skipping creation."
} else {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    Invoke-Expression "$PythonCmd -m venv .venv"
}

Write-Host "Activating virtual environment..."
. ".\.venv\Scripts\Activate.ps1"

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

# ------------------------------------------------------------
# 8. Install Python requirements
# ------------------------------------------------------------
if (Test-Path "requirements.txt") {
    Write-Host "Installing Python requirements from requirements.txt..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
} elseif (Test-Path "requirements.xt") {
    Write-Host "Installing Python requirements from requirements.xt..." -ForegroundColor Yellow
    python -m pip install -r requirements.xt
} else {
    Write-Host "No requirements.txt or requirements.xt found. Skipping Python dependency install."
}

# ------------------------------------------------------------
# 9. Run the app
# ------------------------------------------------------------
Write-Host "Starting Erdstall Admin GUI..." -ForegroundColor Green
python -m erdstall_admin_gui.main