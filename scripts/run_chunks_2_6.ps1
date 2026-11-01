# Runs experiment chunks 2-6 in order (see results/runtime_estimate.md).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_chunks_2_6.ps1 [-DryRun]
param([switch]$DryRun)

$Workers = 10          # fixed by the memory probe: ~48 MB per worker, safe value = min(10, ...) = 10
$MinFreeGB = 2.0
$WaitSeconds = 60
$MaxWaits = 10

Set-Location (Split-Path -Parent $PSScriptRoot)
$LogDir = "results/logs"
$Progress = Join-Path (Get-Location).Path "results\logs\progress.txt"   # absolute: .NET does not follow Set-Location

$Chunks = @(
    @{ N = 2; Name = "ablation_mcts"; Args = "--config experiments/configs/ablation_mcts.yaml --run-dir results/ablation_mcts/full --only 9x5@0.5" },
    @{ N = 3; Name = "scaling";       Args = "--config experiments/configs/scaling.yaml --run-dir results/scaling/full --only 7x4@0.5 9x5@0.5 11x5@0.5" },
    @{ N = 4; Name = "main_7x7";      Args = "--config experiments/configs/main_7x7.yaml --run-dir results/main_7x7/full --only 7x4@0.5" },
    @{ N = 5; Name = "main_9x9 0.1+0.5"; Args = "--config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full --only 9x5@0.1 9x5@0.5" },
    @{ N = 6; Name = "main_9x9 1.0";  Args = "--config experiments/configs/main_9x9.yaml --run-dir results/main_9x9/full --only 9x5@1 --extras" }
)
$Post = @("experiments.plots", "experiments.tables", "experiments.failure_cases", "experiments.nps_hist", "experiments.plot_growth")

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

if (-not $DryRun) { New-Item -ItemType Directory -Force $LogDir | Out-Null }

$oldStandby = $null; $oldHibernate = $null
if ($DryRun) {
    Write-Host "[dry-run] would record current AC standby/hibernate timeouts, then run:"
    Write-Host "[dry-run]   powercfg /change standby-timeout-ac 0"
    Write-Host "[dry-run]   powercfg /change hibernate-timeout-ac 0"
} else {
    $oldStandby = Get-AcMinutes "STANDBYIDLE"
    $oldHibernate = Get-AcMinutes "HIBERNATEIDLE"
    Write-Progress-Line "power settings before: standby-timeout-ac=$oldStandby min, hibernate-timeout-ac=$oldHibernate min"
    powercfg /change standby-timeout-ac 0
    powercfg /change hibernate-timeout-ac 0
}

try {
    foreach ($c in $Chunks) {
        $pyArgs = "-m experiments.run $($c.Args) --workers $Workers"
        $log = "$LogDir/chunk_$($c.N).log"
        if ($DryRun) {
            Write-Host "[dry-run] chunk $($c.N) ($($c.Name)): free RAM check >= $MinFreeGB GB (wait $WaitSeconds s, max $MaxWaits times)"
            Write-Host "[dry-run]   python $pyArgs  >> $log 2>&1   (one retry on non-zero exit)"
            continue
        }
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
        if ($DryRun) { Write-Host "[dry-run] python -m $m >> $LogDir/postprocess.log 2>&1"; continue }
        Write-Progress-Line "post-processing: $m START"
        $code = Invoke-Logged "-m $m" "$LogDir/postprocess.log"
        Write-Progress-Line "post-processing: $m END exit=$code"
    }
}
finally {
    if ($DryRun) {
        Write-Host "[dry-run] finally: restore standby-timeout-ac / hibernate-timeout-ac to the recorded values"
    } else {
        if ($null -ne $oldStandby)   { powercfg /change standby-timeout-ac ([int]$oldStandby) }
        if ($null -ne $oldHibernate) { powercfg /change hibernate-timeout-ac ([int]$oldHibernate) }
        Write-Progress-Line "power settings restored: standby=$oldStandby min, hibernate=$oldHibernate min"
    }
}
