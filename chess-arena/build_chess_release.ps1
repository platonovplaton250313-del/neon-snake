# Build chess-arena\dist\ChessArena.zip - a portable CHESS ARENA folder for Windows.
#
# The archive contains:
#   ChessArena\chess\              game files (incl. chess icons and Stockfish)
#   ChessArena\chess.cmd           launcher
#   ChessArena\install_chess.cmd   installer
#   ChessArena\uninstall_chess.cmd
#   ChessArena\serve_chess.ps1
#   ChessArena\path_tool.ps1
#
# Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File chess-arena\build_chess_release.ps1

[CmdletBinding()]
param(
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
$dist = Join-Path $root 'dist'
$demo = Join-Path $repo 'docs\chess'

if (-not (Test-Path -LiteralPath (Join-Path $demo 'index.html'))) {
    throw "Game files not found: $demo"
}

$standalone = Join-Path $demo 'standalone.html'
if (-not (Test-Path -LiteralPath $standalone)) {
    throw 'standalone.html is missing. Run: python chess-arena\build_chess_standalone.py'
}

if (-not $Output) {
    $Output = Join-Path $dist 'ChessArena.zip'
}
$Output = [System.IO.Path]::GetFullPath($Output)

if (-not (Test-Path -LiteralPath $dist)) {
    New-Item -ItemType Directory -Path $dist | Out-Null
}

$stageRoot = Join-Path $dist '_chess_stage'
$stage = Join-Path $stageRoot 'ChessArena'
if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stage | Out-Null

Copy-Item -LiteralPath $demo -Destination (Join-Path $stage 'chess') -Recurse

$files = @(
    'chess.cmd',
    'install_chess.cmd',
    'uninstall_chess.cmd',
    'serve_chess.ps1',
    'path_tool.ps1'
)
foreach ($file in $files) {
    $source = Join-Path $root $file
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing release file: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $stage $file)
}

try {
    if (Test-Path -LiteralPath $Output) {
        Remove-Item -LiteralPath $Output -Force
    }
    Compress-Archive -Path $stage -DestinationPath $Output -CompressionLevel Optimal

    $item = Get-Item -LiteralPath $Output
    $hash = Get-FileHash -LiteralPath $Output -Algorithm SHA256
    Write-Host ''
    Write-Host 'CHESS ARENA release built' -ForegroundColor Green
    Write-Host "  file : $($item.FullName)"
    Write-Host "  size : $([math]::Round($item.Length / 1MB, 2)) MB"
    Write-Host "  sha  : $($hash.Hash)"
    Write-Host ''
}
finally {
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
