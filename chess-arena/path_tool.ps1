param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('add', 'remove')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Dir,

    # used by automated tests only; the real user PATH is the default
    [string]$KeyPath = 'Environment',

    [switch]$NoBroadcast
)

$ErrorActionPreference = 'Stop'

$dir = $Dir.TrimEnd('\')
$root = [Microsoft.Win32.Registry]::CurrentUser
$key = $root.OpenSubKey($KeyPath, $true)
if (-not $key) {
    $key = $root.CreateSubKey($KeyPath)
}

$cur = ''
$kind = [Microsoft.Win32.RegistryValueKind]::ExpandString
if ($key.GetValueNames() -contains 'Path') {
    $cur = [string]$key.GetValue(
        'Path', '',
        [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    $kind = $key.GetValueKind('Path')
}

$parts = @($cur -split ';' | Where-Object { $_ -ne '' })
$exists = $false
foreach ($p in $parts) {
    if ($p.TrimEnd('\') -ieq $dir) {
        $exists = $true
        break
    }
}

if ($Action -eq 'add') {
    if ($exists) {
        Write-Host "Already in PATH: $dir"
        $key.Close()
        exit 0
    }
    $parts += $dir
    $key.SetValue('Path', ($parts -join ';'), $kind)
    Write-Host "Added to PATH: $dir"
}
else {
    if (-not $exists) {
        Write-Host "Not found in PATH: $dir"
        $key.Close()
        exit 0
    }
    $parts = @($parts | Where-Object { $_.TrimEnd('\') -ine $dir })
    $key.SetValue('Path', ($parts -join ';'), $kind)
    Write-Host "Removed from PATH: $dir"
}
$key.Close()

if (-not $NoBroadcast) {
    try {
        $sig = '[DllImport("user32.dll", SetLastError=true, CharSet=CharSet.Auto)] ' +
               'public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, ' +
               'UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, ' +
               'out UIntPtr lpdwResult);'
        $native = Add-Type -MemberDefinition $sig -Name NativeMethods `
            -Namespace NeonSnake -PassThru -ErrorAction Stop
        $result = [UIntPtr]::Zero
        [void]$native::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero,
            'Environment', 2, 3000, [ref]$result)
        Write-Host 'PATH refreshed for new windows.'
    }
    catch {
        Write-Host 'Note: open a NEW cmd window (or sign out and in) to refresh PATH.'
    }
}

exit 0
