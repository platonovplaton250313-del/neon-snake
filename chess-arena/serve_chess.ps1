# CHESS ARENA - tiny local web server for the chess app.
# Runs without administrator rights and only listens on 127.0.0.1.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File serve_chess.ps1
#   powershell -ExecutionPolicy Bypass -File serve_chess.ps1 -Port 8140 -NoBrowser
#   powershell -ExecutionPolicy Bypass -File serve_chess.ps1 -Check
#
# Close the console window (or press Ctrl+C) to stop the server.

[CmdletBinding()]
param(
    [string]$Root = '',
    [int]$Port = 8137,
    [switch]$NoBrowser,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

function Resolve-ChessLayout {
    param([string]$Base)

    $baseFull = [System.IO.Path]::GetFullPath($Base)
    $candidates = @(
        @{ WebRoot = (Join-Path $baseFull 'docs');    UrlPath = 'chess/' },
        @{ WebRoot = (Join-Path $baseFull '..\docs'); UrlPath = 'chess/' },
        @{ WebRoot = (Join-Path $baseFull 'app');     UrlPath = 'chess/' },
        @{ WebRoot = $baseFull;                       UrlPath = 'chess/' },
        @{ WebRoot = $baseFull;                       UrlPath = '' }
    )

    foreach ($candidate in $candidates) {
        $index = Join-Path $candidate.WebRoot ($candidate.UrlPath + 'index.html')
        if (Test-Path -LiteralPath $index -PathType Leaf) {
            return $candidate
        }
    }
    return $null
}

function Start-ChessListener {
    param([int]$PreferredPort)

    if ($PreferredPort -le 0) { $PreferredPort = 8137 }
    $lastError = ''

    for ($offset = 0; $offset -le 30; $offset++) {
        $candidatePort = $PreferredPort + $offset
        $listener = New-Object System.Net.HttpListener
        $listener.Prefixes.Add("http://127.0.0.1:$candidatePort/")
        try {
            $listener.Start()
            return @{ Listener = $listener; Port = $candidatePort }
        }
        catch {
            $lastError = $_.Exception.Message
            $listener.Close()
        }
    }

    throw "Could not open a local port. Last error: $lastError"
}

function Send-ChessResponse {
    param(
        $Context,
        [int]$Status,
        [byte[]]$Bytes,
        [string]$ContentType,
        [string]$CacheControl = 'no-cache'
    )

    $response = $Context.Response
    $response.StatusCode = $Status
    $response.ContentType = $ContentType
    $response.ContentLength64 = $Bytes.Length
    $response.Headers['Cache-Control'] = $CacheControl
    $response.Headers['X-Content-Type-Options'] = 'nosniff'
    if ($Context.Request.HttpMethod -ne 'HEAD' -and $Bytes.Length -gt 0) {
        $response.OutputStream.Write($Bytes, 0, $Bytes.Length)
    }
    $response.OutputStream.Close()
}

function Send-ChessText {
    param($Context, [int]$Status, [string]$Text, [string]$ContentType = 'text/plain; charset=utf-8')

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    Send-ChessResponse -Context $Context -Status $Status -Bytes $bytes -ContentType $ContentType
}

function Send-ChessFile {
    param($Context, [string]$FullPath)

    $mime = @{
        '.html'        = 'text/html; charset=utf-8'
        '.htm'         = 'text/html; charset=utf-8'
        '.css'         = 'text/css; charset=utf-8'
        '.js'          = 'text/javascript; charset=utf-8'
        '.json'        = 'application/json; charset=utf-8'
        '.wasm'        = 'application/wasm'
        '.webmanifest' = 'application/manifest+json; charset=utf-8'
        '.svg'         = 'image/svg+xml'
        '.png'         = 'image/png'
        '.jpg'         = 'image/jpeg'
        '.jpeg'        = 'image/jpeg'
        '.gif'         = 'image/gif'
        '.ico'         = 'image/x-icon'
        '.woff'        = 'font/woff'
        '.woff2'       = 'font/woff2'
        '.ttf'         = 'font/ttf'
        '.mp3'         = 'audio/mpeg'
        '.wav'         = 'audio/wav'
        '.ogg'         = 'audio/ogg'
        '.txt'         = 'text/plain; charset=utf-8'
        '.map'         = 'application/json; charset=utf-8'
    }

    $extension = [System.IO.Path]::GetExtension($FullPath).ToLowerInvariant()
    $contentType = if ($mime.ContainsKey($extension)) { $mime[$extension] } else { 'application/octet-stream' }
    $bytes = [System.IO.File]::ReadAllBytes($FullPath)
    Send-ChessResponse -Context $Context -Status 200 -Bytes $bytes -ContentType $contentType
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$base = if ($Root) { $Root } else { $scriptDir }
$layout = Resolve-ChessLayout -Base $base

if (-not $layout) {
    Write-Host '[chess] Could not find the game files.' -ForegroundColor Red
    Write-Host "        Looked next to: $base"
    Write-Host '        Expected one of:'
    Write-Host '          docs\chess\index.html'
    Write-Host '          ..\docs\chess\index.html'
    Write-Host '          app\chess\index.html'
    Write-Host '          chess\index.html'
    Write-Host '          index.html'
    exit 1
}

$webRoot = [System.IO.Path]::GetFullPath($layout.WebRoot).TrimEnd('\')
$urlPath = $layout.UrlPath

if ($Check) {
    Write-Host 'CHESS ARENA launcher check'
    Write-Host "  base  : $base"
    Write-Host "  files : $webRoot"
    Write-Host "  url   : http://127.0.0.1:$Port/$urlPath"
    exit 0
}

try {
    $server = Start-ChessListener -PreferredPort $Port
}
catch {
    Write-Host ''
    Write-Host '[chess] Could not start the local server.' -ForegroundColor Red
    Write-Host "        $($_.Exception.Message)"
    Write-Host '        Try another port: chess -Port 8145'
    Write-Host ''
    exit 1
}

$listener = $server.Listener
$url = "http://127.0.0.1:$($server.Port)/$urlPath"

Write-Host ''
Write-Host '  CHESS ARENA' -ForegroundColor Green
Write-Host "  $url" -ForegroundColor Cyan
Write-Host "  Files: $webRoot"
Write-Host ''
Write-Host '  This window is the local server. Close it to stop the game.'
Write-Host ''

if (-not $NoBrowser) {
    try {
        Start-Process $url
    }
    catch {
        Write-Host "  Open this address manually: $url"
    }
}

$webRootPrefix = $webRoot + [System.IO.Path]::DirectorySeparatorChar

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        try {
            $method = $context.Request.HttpMethod
            if ($method -ne 'GET' -and $method -ne 'HEAD') {
                Send-ChessText -Context $context -Status 405 -Text 'Method not allowed'
                continue
            }

            $rawPath = $context.Request.Url.AbsolutePath
            if ($urlPath -and ($rawPath -eq '/' -or $rawPath -eq '')) {
                $context.Response.StatusCode = 302
                $context.Response.RedirectLocation = "/$urlPath"
                $context.Response.Headers['Cache-Control'] = 'no-store'
                $context.Response.Close()
                continue
            }

            $relative = [System.Uri]::UnescapeDataString($rawPath).TrimStart('/')
            if ($relative -eq '') {
                $relative = 'index.html'
            }
            $relative = $relative.Replace('/', '\')
            $fullPath = [System.IO.Path]::GetFullPath((Join-Path $webRoot $relative))

            if (-not ($fullPath -eq $webRoot -or $fullPath.StartsWith($webRootPrefix, [System.StringComparison]::OrdinalIgnoreCase))) {
                Send-ChessText -Context $context -Status 403 -Text 'Forbidden'
                continue
            }

            if (Test-Path -LiteralPath $fullPath -PathType Container) {
                if (-not $rawPath.EndsWith('/')) {
                    $context.Response.StatusCode = 302
                    $context.Response.RedirectLocation = $rawPath + '/'
                    $context.Response.Headers['Cache-Control'] = 'no-store'
                    $context.Response.Close()
                    continue
                }
                $fullPath = Join-Path $fullPath 'index.html'
            }

            if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
                $notFound = @'
<!doctype html>
<html lang="ru"><meta charset="utf-8"><title>404</title>
<body style="background:#262421;color:#e8e5e0;font:16px/1.5 system-ui,sans-serif;padding:40px">
<h1>404</h1><p>Файл не найден.</p><p><a style="color:#9fc96d" href="/">CHESS ARENA</a></p>
</body></html>
'@
                Send-ChessText -Context $context -Status 404 -Text $notFound -ContentType 'text/html; charset=utf-8'
                continue
            }

            Send-ChessFile -Context $context -FullPath $fullPath
        }
        catch {
            try {
                Send-ChessText -Context $context -Status 500 -Text 'Internal server error'
            }
            catch {
                # Browser closed the connection; nothing else to do.
            }
        }
    }
}
finally {
    try {
        $listener.Stop()
        $listener.Close()
    }
    catch {
        # Already closed.
    }
    Write-Host ''
    Write-Host '  CHESS ARENA server stopped.'
}
