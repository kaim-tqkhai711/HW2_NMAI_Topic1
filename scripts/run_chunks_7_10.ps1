# Runs experiment chunks 7-11 in order (see results/runtime_estimate.md), then plots/tables/failure cases.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_chunks_7_10.ps1 [-DryRun]
# -DryRun runs nothing: it prints the commands and the calibrated time estimate of every chunk.
param([switch]$DryRun)

$Workers = 10          # fixed by the memory probe: ~48 MB per worker, safe value = min(10, ...) = 10
$MinFreeGB = 2.0
$WaitSeconds = 60
$MaxWaits = 10
$LimitHours = 12.0     # if the estimated total exceeds this, the dry-run proposes cuts

Set-Location (Split-Path -Parent $PSScriptRoot)
$LogDir = "results/logs"
$Progress = Join-Path (Get-Location).Path "results\logs\progress.txt"   # absolute: .NET does not follow Set-Location

$Chunks = @(
    @{ N = 7;  Name = "main_11x11";     Args = "--config experiments/configs/main_11x11.yaml --run-dir results/main_11x11/full --only 11x5@0.5" },
    @{ N = 8;  Name = "failure_mining"; Args = "--config experiments/configs/failure_mining.yaml --run-dir results/failure_mining/full --only 7x4@0.1" },
    @{ N = 9;  Name = "nodes_budget 7x4"; Args = "--config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 7x4@2000 7x4@10000" },
    @{ N = 10; Name = "nodes_budget 9x5@2000"; Args = "--config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 9x5@2000" },
    # replicate of the 0.1 s cell with 6 workers (the 10-worker cell was budget-noisy); separate run dir, nothing overwritten
    @{ N = 11; Name = "main_9x9 0.1 s, 6 workers"; Workers = 6; Args = "--config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full_w6_0.1 --only 9x5@0.1" }
)
$Post = @("experiments.plots", "experiments.tables", "experiments.failure_cases")

function Append-SharedLine([string]$Path, [string]$Line) {
    # FileShare.ReadWrite: a reader such as `Get-Content -Wait` must not block the log; retry, never abort the run
    for ($i = 1; $i -le 5; $i++) {
        try {
            $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
            try {
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($Line + [Environment]::NewLine)
                $fs.Write($bytes, 0, $bytes.Length)
            } finally { $fs.Dispose() }
            return
        } catch [System.IO.IOException] { Start-Sleep -Milliseconds (200 * $i) }
    }
    Write-Host "(could not append to $Path after 5 tries)"
}

function Write-Progress-Line([string]$Text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Text
    Write-Host $line
    if (-not $DryRun) { Append-SharedLine $Progress $line }
}

function Get-FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2) }

function Get-AcMinutes([string]$Setting) {
    $out = powercfg /q SCHEME_CURRENT SUB_SLEEP $Setting | Out-String
    if ($out -match "Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)") { return [Convert]::ToInt32($Matches[1], 16) / 60 }
    return $null
}

function Invoke-Logged([string]$PyArgs, [string]$Log) {
    # cmd does the redirection so that PowerShell 5.1 does not turn stderr lines into error records
    cmd /c "python $PyArgs >> `"$Log`" 2>&1"
    return $LASTEXITCODE
}

function Get-ChunkHours([string]$PyArgs) {
    # the runner's own dry-run: respects --only and prints calibrated_hours=<h>
    $out = cmd /c "python $PyArgs --dry-run 2>&1" | Out-String
    if ($out -match "calibrated_hours=([0-9.]+)") { return [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture) }
    Write-Host $out
    return $null
}

if (-not $DryRun) { New-Item -ItemType Directory -Force $LogDir | Out-Null }

if ($DryRun) {
    Write-Host "[dry-run] would record current AC standby/hibernate timeouts, then run:"
    Write-Host "[dry-run]   powercfg /change standby-timeout-ac 0"
    Write-Host "[dry-run]   powercfg /change hibernate-timeout-ac 0"
    $total = 0.0
    foreach ($c in $Chunks) {
        $w = if ($c.Workers) { $c.Workers } else { $Workers }
        $pyArgs = "-m experiments.run $($c.Args) --workers $w"
        Write-Host "[dry-run] chunk $($c.N) ($($c.Name)): free RAM check >= $MinFreeGB GB (wait $WaitSeconds s, max $MaxWaits times)"
        Write-Host "[dry-run]   python $pyArgs  >> $LogDir/chunk_$($c.N).log 2>&1   (one retry on non-zero exit)"
        $h = Get-ChunkHours $pyArgs
        if ($null -eq $h) { Write-Host "[dry-run]   estimate unavailable"; continue }
        $total += $h
        Write-Host ("[dry-run]   estimated {0:N2} h ({1:N0} min)" -f $h, ($h * 60))
    }
    foreach ($m in $Post) { Write-Host "[dry-run] python -m $m >> $LogDir/postprocess.log 2>&1" }
    Write-Host "[dry-run] finally: restore standby-timeout-ac / hibernate-timeout-ac to the recorded values"
    Write-Host ("[dry-run] TOTAL estimated {0:N2} h (limit {1:N0} h)" -f $total, $LimitHours)
    if ($total -gt $LimitHours) {
        Write-Host "[dry-run] over the limit: drop chunk 11 first, then chunk 10 (nodes_budget 9x5@2000), then 7x4@10000 from chunk 9"
    }
    return
}

$oldStandby = Get-AcMinutes "STANDBYIDLE"
$oldHibernate = Get-AcMinutes "HIBERNATEIDLE"
Write-Progress-Line "power settings before: standby-timeout-ac=$oldStandby min, hibernate-timeout-ac=$oldHibernate min"
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

try {
    foreach ($c in $Chunks) {
        $w = if ($c.Workers) { $c.Workers } else { $Workers }
        $pyArgs = "-m experiments.run $($c.Args) --workers $w"
        $log = "$LogDir/chunk_$($c.N).log"
        $waits = 0
        while ($true) {
            $free = Get-FreeGB
            Write-Progress-Line "chunk $($c.N) ($($c.Name)): free RAM $free GB"
            if ($free -ge $MinFreeGB -or $waits -ge $MaxWaits) { break }
            $waits++
            Write-Progress-Line "chunk $($c.N): free RAM below $MinFreeGB GB, waiting $WaitSeconds s ($waits/$MaxWaits)"
            Start-Sleep -Seconds $WaitSeconds
        }
        if ($free -lt $MinFreeGB) { Write-Progress-Line "chunk $($c.N): still low on RAM after $MaxWaits waits, running anyway" }

        $code = 1
        foreach ($attempt in 1..2) {
            Write-Progress-Line "chunk $($c.N) ($($c.Name)) START attempt $attempt"
            $code = Invoke-Logged $pyArgs $log
            Write-Progress-Line "chunk $($c.N) ($($c.Name)) END attempt $attempt exit=$code"
            if ($code -eq 0) { break }
        }
        if ($code -ne 0) { Write-Progress-Line "chunk $($c.N) ($($c.Name)) FAILED after retry, continuing with the next chunk" }
    }

    foreach ($m in $Post) {
        Write-Progress-Line "post-processing: $m START"
        $code = Invoke-Logged "-m $m" "$LogDir/postprocess.log"
        Write-Progress-Line "post-processing: $m END exit=$code"
    }
}
finally {
    if ($null -ne $oldStandby)   { powercfg /change standby-timeout-ac ([int]$oldStandby) }
    if ($null -ne $oldHibernate) { powercfg /change hibernate-timeout-ac ([int]$oldHibernate) }
    Write-Progress-Line "power settings restored: standby=$oldStandby min, hibernate=$oldHibernate min"
}
