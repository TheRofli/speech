param(
    [string] $Repository = "TheRofli/speech",
    [string] $Branch = "main",
    [string] $InstallDir = "D:\Speech",
    [switch] $DownloadParakeet
)

$ErrorActionPreference = "Stop"

function Assert-SafeTempPath {
    param([string] $Path)
    $resolved = [System.IO.Path]::GetFullPath($Path)
    $temp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    if (-not $resolved.StartsWith($temp, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to use temp path outside system temp: $resolved"
    }
}

$zipUrl = "https://github.com/$Repository/archive/refs/heads/$Branch.zip"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("speech-install-" + [System.Guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot "speech.zip"

Assert-SafeTempPath $tempRoot
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

try {
    Write-Host "Downloading Speech from $zipUrl"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath

    Write-Host "Extracting..."
    Expand-Archive -LiteralPath $zipPath -DestinationPath $tempRoot -Force
    $source = Get-ChildItem -LiteralPath $tempRoot -Directory |
        Where-Object { $_.Name -like "Speech-*" -or $_.Name -like "speech-*" } |
        Select-Object -First 1
    if (-not $source) {
        throw "Could not find extracted Speech source folder."
    }

    Write-Host "Installing to $InstallDir"
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Get-ChildItem -LiteralPath $source.FullName -Force |
        Copy-Item -Destination $InstallDir -Recurse -Force

    & (Join-Path $InstallDir "install.ps1")

    if ($DownloadParakeet) {
        & (Join-Path $InstallDir "bin\speech.cmd") parakeet install
    }

    Write-Host ""
    Write-Host "Speech is installed."
    Write-Host "Start it with: speech"
    Write-Host "Download Parakeet later with: speech parakeet install"
}
finally {
    Assert-SafeTempPath $tempRoot
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
