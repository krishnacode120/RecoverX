$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) { throw 'GitHub Actions runner required.' }
$installRoot = Join-Path $env:RUNNER_TEMP ('recoverx-installed-' + [guid]::NewGuid().ToString('N'))
function Run-Checked($file, $arguments) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(120000)) { $process.Kill(); throw "Timed out: $file" }
    if ($process.ExitCode -ne 0) { throw "Failed ($($process.ExitCode)): $file" }
}
$setup = Join-Path $PSScriptRoot '..\dist\installer\RecoverX-Setup-0.3.0.exe'
Run-Checked $setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/DIR=""$installRoot""")
$app = Join-Path $installRoot 'RecoverX.exe'
if (-not (Test-Path -LiteralPath $app)) { throw 'Installed executable missing.' }
Run-Checked $app @('--smoke-test')
Run-Checked (Join-Path $installRoot 'unins000.exe') @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
if (Test-Path -LiteralPath $app) { throw 'Uninstall left the executable behind.' }
Write-Output 'Silent install, installed startup and uninstall passed on the Windows runner.'
