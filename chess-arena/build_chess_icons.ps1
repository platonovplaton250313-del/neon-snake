# Build CHESS ARENA PWA icons (PNG) with the built-in .NET drawing library.
# Usage: powershell -ExecutionPolicy Bypass -File build_chess_icons.ps1

[CmdletBinding()]
param(
    [string]$OutDir = ''
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
if (-not $OutDir) { $OutDir = Join-Path $repo 'docs\chess\icons' }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function New-RoundedPath {
    param([single]$X, [single]$Y, [single]$W, [single]$H, [single]$R)
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $d = $R * 2
    $path.AddArc($X, $Y, $d, $d, 180, 90)
    $path.AddArc($X + $W - $d, $Y, $d, $d, 270, 90)
    $path.AddArc($X + $W - $d, $Y + $H - $d, $d, $d, 0, 90)
    $path.AddArc($X, $Y + $H - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-ChessIcon {
    param([int]$Size, [string]$Path, [switch]$FullBleed)

    $bmp = [System.Drawing.Bitmap]::new($Size, $Size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.Clear([System.Drawing.Color]::Transparent)

    $s = $Size / 512.0
    if ($FullBleed) {
        $shape = [System.Drawing.Drawing2D.GraphicsPath]::new()
        $shape.AddRectangle([System.Drawing.RectangleF]::new(0, 0, $Size, $Size))
    } else {
        $radius = [single]($Size * 0.19)
        $shape = New-RoundedPath 0 0 $Size $Size $radius
    }

    # Green gradient background.
    $rect = [System.Drawing.RectangleF]::new(0, 0, $Size, $Size)
    $c1 = [System.Drawing.Color]::FromArgb(255, 150, 202, 93)
    $c2 = [System.Drawing.Color]::FromArgb(255, 83, 125, 47)
    $bg = [System.Drawing.Drawing2D.LinearGradientBrush]::new($rect, $c1, $c2, 55.0)
    $g.FillPath($bg, $shape)

    # Subtle checkerboard inside the rounded square.
    $oldClip = $g.Clip
    $g.SetClip($shape)
    $cell = $Size / 8.0
    for ($row = 0; $row -lt 8; $row++) {
        for ($col = 0; $col -lt 8; $col++) {
            if ((($row + $col) % 2) -eq 0) {
                $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(16, 255, 255, 255))
            } else {
                $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(12, 20, 40, 10))
            }
            $g.FillRectangle($brush, [single]($col * $cell), [single]($row * $cell), [single]$cell, [single]$cell)
            $brush.Dispose()
        }
    }
    $g.Clip = $oldClip

    # Soft shadow under the pawn.
    $shadow = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(46, 0, 0, 0))
    $g.FillEllipse($shadow, [single](135 * $s), [single](392 * $s), [single](242 * $s), [single](56 * $s))
    $shadow.Dispose()

    $fill = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 245, 248, 236))
    $pen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(255, 47, 74, 30), [single](11 * $s))
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round

    # Head.
    $headRect = [System.Drawing.RectangleF]::new([single](182 * $s), [single](74 * $s), [single](148 * $s), [single](148 * $s))
    $g.FillEllipse($fill, $headRect)
    $g.DrawEllipse($pen, $headRect)

    # Neck.
    $neck = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $neck.AddPolygon([System.Drawing.PointF[]]@(
        [System.Drawing.PointF]::new([single](219 * $s), [single](211 * $s)),
        [System.Drawing.PointF]::new([single](293 * $s), [single](211 * $s)),
        [System.Drawing.PointF]::new([single](306 * $s), [single](286 * $s)),
        [System.Drawing.PointF]::new([single](206 * $s), [single](286 * $s))
    ))
    $g.FillPath($fill, $neck)
    $g.DrawPath($pen, $neck)

    # Collar.
    $collar = New-RoundedPath ([single](188 * $s)) ([single](276 * $s)) ([single](136 * $s)) ([single](32 * $s)) ([single](12 * $s))
    $g.FillPath($fill, $collar)
    $g.DrawPath($pen, $collar)

    # Body.
    $body = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $body.AddPolygon([System.Drawing.PointF[]]@(
        [System.Drawing.PointF]::new([single](215 * $s), [single](303 * $s)),
        [System.Drawing.PointF]::new([single](297 * $s), [single](303 * $s)),
        [System.Drawing.PointF]::new([single](320 * $s), [single](374 * $s)),
        [System.Drawing.PointF]::new([single](192 * $s), [single](374 * $s))
    ))
    $g.FillPath($fill, $body)
    $g.DrawPath($pen, $body)

    # Base plates.
    $base1 = New-RoundedPath ([single](163 * $s)) ([single](363 * $s)) ([single](186 * $s)) ([single](44 * $s)) ([single](14 * $s))
    $g.FillPath($fill, $base1)
    $g.DrawPath($pen, $base1)
    $base2 = New-RoundedPath ([single](141 * $s)) ([single](397 * $s)) ([single](230 * $s)) ([single](40 * $s)) ([single](12 * $s))
    $g.FillPath($fill, $base2)
    $g.DrawPath($pen, $base2)

    # Highlight.
    $highlight = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(90, 255, 255, 255))
    $g.FillEllipse($highlight, [single](208 * $s), [single](97 * $s), [single](44 * $s), [single](30 * $s))
    $highlight.Dispose()

    $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)

    $pen.Dispose()
    $fill.Dispose()
    $neck.Dispose()
    $collar.Dispose()
    $body.Dispose()
    $base1.Dispose()
    $base2.Dispose()
    $bg.Dispose()
    $shape.Dispose()
    $g.Dispose()
    $bmp.Dispose()
}

New-ChessIcon -Size 32 -Path (Join-Path $OutDir 'favicon.png')
New-ChessIcon -Size 64 -Path (Join-Path $OutDir 'favicon-64.png')
New-ChessIcon -Size 180 -Path (Join-Path $OutDir 'apple-touch-icon.png')
New-ChessIcon -Size 192 -Path (Join-Path $OutDir 'icon-192.png')
New-ChessIcon -Size 512 -Path (Join-Path $OutDir 'icon-512.png')
New-ChessIcon -Size 512 -Path (Join-Path $OutDir 'icon-maskable-512.png') -FullBleed

Get-ChildItem -LiteralPath $OutDir -Filter *.png | Select-Object Name, Length
