# CI-only fixture creation: storage mutations target a new, path-verified VHD.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) { throw 'GitHub Actions runner required.' }
$fixtureRoot = Join-Path $env:RUNNER_TEMP ('recoverx-fixture-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
$vhd = Join-Path $fixtureRoot 'deleted-files.vhd'
$diskScript = Join-Path $fixtureRoot 'create.txt'
$scriptRoot = $PSScriptRoot
$attached = $false
try {
    @("create vdisk file=""$vhd"" maximum=128 type=fixed", 'exit') | Set-Content -LiteralPath $diskScript -Encoding ascii
    & diskpart.exe /s $diskScript
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $vhd)) { throw 'VHD creation failed.' }
    $image = Mount-DiskImage -ImagePath $vhd -Access ReadWrite -PassThru
    $attached = $true
    $disk = $image | Get-Disk
    if ($disk.IsBoot -or $disk.IsSystem -or $disk.PartitionStyle -ne 'RAW' -or $disk.Size -gt 129MB) {
        throw 'Fixture disk identity/geometry guard rejected storage mutation.'
    }
    if ([IO.Path]::GetFullPath($image.ImagePath) -ne [IO.Path]::GetFullPath($vhd)) { throw 'Wrong disk image.' }
    $disk | Initialize-Disk -PartitionStyle MBR
    $partition = $disk | New-Partition -UseMaximumSize -AssignDriveLetter
    $volume = $partition | Format-Volume -FileSystem NTFS -NewFileSystemLabel 'RecoverX-CI' -Confirm:$false -Force
    $letter = [string]$volume.DriveLetter
    if ($letter -notmatch '^[A-Z]$' -or ('{0}:' -f $letter) -eq $env:SystemDrive) { throw 'Unsafe fixture mount.' }
    & python "$scriptRoot/windows_recovery_ci.py" prepare ('{0}:\' -f $letter)
    if ($LASTEXITCODE -ne 0) { throw 'Fixture file preparation failed.' }
    Dismount-DiskImage -ImagePath $vhd
    $attached = $false
    $before = (Get-FileHash -LiteralPath $vhd -Algorithm SHA256).Hash
    $image = Mount-DiskImage -ImagePath $vhd -Access ReadOnly -PassThru
    $attached = $true
    $disk = $image | Get-Disk
    if ($disk.IsBoot -or $disk.IsSystem -or -not $disk.IsReadOnly) { throw 'Read-only fixture guard failed.' }
    $partitions = @($disk | Get-Partition | Where-Object DriveLetter)
    if ($partitions.Count -ne 1) { throw 'Expected one mounted fixture partition.' }
    $letter = [string]$partitions[0].DriveLetter
    & python "$scriptRoot/windows_recovery_ci.py" drive "$letter" "$($disk.Number)"
    if ($LASTEXITCODE -ne 0) { throw 'Real Windows drive-reader recovery failed.' }
    Dismount-DiskImage -ImagePath $vhd
    $attached = $false
    if ((Get-FileHash -LiteralPath $vhd -Algorithm SHA256).Hash -ne $before) { throw 'Read-only scan changed fixture.' }
    & python "$scriptRoot/windows_recovery_ci.py" image "$vhd" "$fixtureRoot"
    if ($LASTEXITCODE -ne 0) { throw 'Windows-deleted image recovery failed.' }
} finally {
    if ($attached) { Dismount-DiskImage -ImagePath $vhd }
    # Ephemeral runner cleanup owns the fixture; no computed recursive deletion.
}
