param(
    [Parameter(Mandatory = $true)]
    [string]$WindowsPath
)

$windowsPathTrimmed = $WindowsPath.Trim()

if ($windowsPathTrimmed -notmatch '^[A-Za-z]:\\') {
    Write-Error "Expected a drive-rooted Windows path like D:\\path, got: $WindowsPath"
    exit 1
}

$driveLetter = $windowsPathTrimmed.Substring(0, 1).ToLowerInvariant()
$rest = $windowsPathTrimmed.Substring(2).Replace('\', '/')
$wslPath = "/mnt/$driveLetter$rest"

Write-Host "Opening workspace in WSL: $wslPath"

# Validate the directory exists in WSL and `code` is available.
wsl.exe bash -lc "test -d '$wslPath'" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "WSL path not found: $wslPath (is /mnt/$driveLetter mounted?)"
    exit 2
}

wsl.exe bash -lc "command -v code >/dev/null 2>&1"
if ($LASTEXITCODE -ne 0) {
    Write-Error "The 'code' command is not available in WSL. Install the VS Code 'Remote - WSL' extension and try again."
    exit 3
}

# Launch VS Code in WSL context
wsl.exe bash -lc "cd '$wslPath' && code ."
