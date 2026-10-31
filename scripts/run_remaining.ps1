# Runs what is left after chunks 7-9 (see results/runtime_estimate.md): chunk 11, the 10 missing games of
# chunk 9, chunk 10, then plots/tables/failure cases. Every step is resumable: rerun the script after any interruption.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_remaining.ps1 [-DryRun]
# -DryRun runs nothing: it prints the commands and the calibrated time estimate of every step.
param([switch]$DryRun)

$Workers = 10          # memory probe: ~48 MB per worker
$MinFreeGB = 2.0
$WaitSeconds = 60
$MaxWaits = 10
$StallMinutes = 20     # watchdog: a games file that does not grow for this long means a stalled pool

Set-Location (Split-Path -Parent $PSScriptRoot)
$LogDir = "results/logs"
$Progress = Join-Path (Get-Location).Path "results\logs\progress.txt"   # absolute: .NET does not follow Set-Location

# Order: short and important first. Chunk 11 writes to its own run dir (the 10-worker 0.1 s cell was budget-noisy).
$Chunks = @(
    @{ Label = "A"; N = 11; Name = "main_9x9 0.1 s, 6 workers"; Workers = 6; Watch = "results/main_9x9/full_w6_0.1/games.jsonl"; Ids = @('{"game_id":"9x5|t0.1|')
       Args = "--config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full_w6_0.1 --only 9x5@0.1" },
    @{ Label = "B"; N = 9;  Name = "nodes_budget 7x4 (10 missing games)"; Watch = "results/nodes_budget/full/games.jsonl"; Ids = @('{"game_id":"7x4|n2000|', '{"game_id":"7x4|n10000|')
       Args = "--config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 7x4@2000 7x4@10000" },
    @{ Label = "C"; N = 10; Name = "nodes_budget 9x5@2000"; Watch = "results/nodes_budget/full/games.jsonl"; Ids = @('{"game_id":"9x5|n2000|')
       Args = "--config experiments/configs/nodes_budget.yaml --run-dir results/nodes_budget/full --only 9x5@2000" }
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

function Invoke-Logged([string]$PyArgs, [string]$Log, [string]$Watch = "") {
    # cmd does the redirection so that PowerShell 5.1 does not turn stderr lines into error records.
    # Watchdog (only when $Watch names a growing file): no growth for $StallMinutes -> kill the process tree;
    # the caller's second attempt then resumes from the finished game ids (chunk 9 stalled for 3.3 h unnoticed).
    $p = Start-Process -FilePath "cmd.exe" -ArgumentList "/c python $PyArgs >> `"$Log`" 2>&1" -NoNewWindow -PassThru
    $null = $p.Handle   # PowerShell 5.1 loses ExitCode unless the handle is cached
    $lastLen = -1; $lastChange = Get-Date
    while (-not $p.WaitForExit(30000)) {
        if ($Watch -ne "" -and (Test-Path $Watch)) {
            $fs = [System.IO.File]::Open($Watch, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            try { $len = $fs.Length } finally { $fs.Dispose() }
            if ($len -ne $lastLen) { $lastLen = $len; $lastChange = Get-Date }
            elseif (((Get-Date) - $lastChange).TotalMinutes -ge $StallMinutes) {
                Write-Progress-Line "WATCHDOG: $Watch has not grown for $StallMinutes min, killing process tree $($p.Id)"
                taskkill /T /F /PID $p.Id | Out-Null
                $p.WaitForExit()
                return 124
            }
        }
    }
    return $p.ExitCode
}

function Get-DoneGames([string]$File, [string[]]$Prefixes) {
    if (-not (Test-Path $File)) { return 0 }
    $n = 0
    foreach ($line in [System.IO.File]::ReadLines((Resolve-Path $File).Path)) {
        foreach ($pre in $Prefixes) { if ($line.StartsWith($pre)) { $n++; break } }
    }
    return $n
}

function Get-ChunkPlan([hashtable]$C, [string]$PyArgs) {
    # the runner's own dry-run (respects --only, prints "N games" and calibrated_hours=<h>), scaled by the
    # fraction of games not yet in the games file, so a resumed step reports only what is left
    $out = cmd /c "python $PyArgs --dry-run 2>&1" | Out-String
    if ($out -notmatch "calibrated_hours=([0-9.]+)") { Write-Host $out; return $null }
    $full = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture)
    $total = if ($out -match "(\d+) games in") { [int]$Matches[1] } else { 0 }
    $done = Get-DoneGames $C.Watch $C.Ids
    $left = if ($total -gt 0) { [math]::Max(0, $total - $done) } else { $total }
    $h = if ($total -gt 0) { $full * $left / $total } else { $full }
    return @{ Hours = $h; Full = $full; Total = $total; Done = $done }
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
        Write-Host "[dry-run] step $($c.Label) = chunk $($c.N) ($($c.Name)): free RAM check >= $MinFreeGB GB (wait $WaitSeconds s, max $MaxWaits times)"
        Write-Host "[dry-run]   python $pyArgs  >> $LogDir/chunk_$($c.N).log 2>&1   (watchdog $StallMinutes min, one retry on non-zero exit)"
        $plan = Get-ChunkPlan $c $pyArgs
        if ($null -eq $plan) { Write-Host "[dry-run]   estimate unavailable"; continue }
        $total += $plan.Hours
        Write-Host ("[dry-run]   {0} of {1} games done; estimated remaining {2:N2} h ({3:N0} min) (full step {4:N2} h)" -f $plan.Done, $plan.Total, $plan.Hours, ($plan.Hours * 60), $plan.Full)
    }
    foreach ($m in $Post) { Write-Host "[dry-run] python -m $m >> $LogDir/postprocess.log 2>&1" }
    Write-Host "[dry-run] finally: restore standby-timeout-ac / hibernate-timeout-ac to the recorded values"
    Write-Host ("[dry-run] TOTAL estimated {0:N2} h (steps A-C, post-processing about 1 min)" -f $total)
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

        $plan = Get-ChunkPlan $c $pyArgs
        if ($null -ne $plan) {
            Write-Progress-Line ("step {0} / chunk {1} ({2}): EXPECTED {3:N2} h ({4:N0} min) for the {5} games left of {6}" -f $c.Label, $c.N, $c.Name, $plan.Hours, ($plan.Hours * 60), ($plan.Total - $plan.Done), $plan.Total)
        }

        $code = 1
        foreach ($attempt in 1..2) {
            Write-Progress-Line "chunk $($c.N) ($($c.Name)) START attempt $attempt"
            $code = Invoke-Logged $pyArgs $log $c.Watch
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
