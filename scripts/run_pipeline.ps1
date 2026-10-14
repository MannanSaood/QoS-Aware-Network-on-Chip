param(
    [string]$Distro = 'Ubuntu-24.04',
    [string]$MatlabExe = '',
    [int]$Jobs = 4,
    [switch]$Setup,
    [switch]$PlotOnly,
    [switch]$LegacyPrimary,
    [switch]$IncludeSecondary
)
$ErrorActionPreference = 'Stop'
$repoDir = Split-Path -Parent $PSScriptRoot
$linuxRepo = (& wsl -d $Distro -- wslpath -a $repoDir).Trim()
if ($LegacyPrimary -and -not $PlotOnly) { throw 'The legacy implementation is archived. Use -LegacyPrimary -PlotOnly to preserve its measured results.' }
$report = if ($LegacyPrimary) { 'primary_report' } else { 'fair_report' }
if ($Setup) {
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/setup.py"
    if ($LASTEXITCODE -ne 0) { throw 'Simulator setup failed' }
}
if (-not $PlotOnly) {
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/validate_booksim_traffic.py"
    if ($LASTEXITCODE -ne 0) { throw 'BookSim traffic generator checks failed' }
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/run_fair_grid.py" --jobs $Jobs
    if ($LASTEXITCODE -ne 0) { throw 'Corrected BookSim sweep failed; inspect results/fair_comparison/cases' }
}
if ($LegacyPrimary) {
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/prepare_primary_results.py"
} else {
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/prepare_fair_results.py"
}
if ($LASTEXITCODE -ne 0) { throw 'Dataset validation failed; the complete matching study is required' }
if ($IncludeSecondary -and -not $PlotOnly) {
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/run_scaling.py" --jobs $Jobs --timeout-seconds 1800
    if ($LASTEXITCODE -ne 0) { throw 'Simulations failed; inspect results/scaling/cases' }
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/run_scaling.py" --jobs $Jobs --sizes 8 --loads 0.05 0.1 0.2 0.3 0.4 0.5 --traffic transpose --warmup 1000 --cycles 3000 --output "$linuxRepo/results/transpose_load"
    if ($LASTEXITCODE -ne 0) { throw 'Transpose simulations failed' }
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/run_scaling.py" --jobs $Jobs --sizes 8 --loads 0.05 0.1 0.2 0.3 0.4 0.5 --traffic uniform bursty hotspot_corner hotspot_edge hotspot_center --warmup 1000 --cycles 3000 --output "$linuxRepo/results/workloads"
    if ($LASTEXITCODE -ne 0) { throw 'Workload simulations failed' }
}
if ($IncludeSecondary) {
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/validate_results.py"
    if ($LASTEXITCODE -ne 0) { throw 'Secondary dataset validation failed' }
    & wsl -d $Distro -- python3 "$linuxRepo/scripts/prepare_model_comparison.py"
    if ($LASTEXITCODE -ne 0) { throw 'Simulator model comparison preparation failed' }
}
if (-not $MatlabExe) {
    $matlabCommand = Get-Command matlab -ErrorAction SilentlyContinue
    if ($matlabCommand) { $MatlabExe = $matlabCommand.Source }
    if (-not $MatlabExe) {
        $installations = Get-ChildItem 'C:/Program Files/MATLAB' -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($installation in $installations) {
            $candidate = Join-Path $installation.FullName 'bin/matlab.exe'
            if (Test-Path -LiteralPath $candidate) { $MatlabExe = $candidate; break }
        }
    }
}
if ($MatlabExe) {
    $matlabRepo = $repoDir.Replace("'", "''").Replace('\','/')
    & $MatlabExe -wait -nojvm -noFigureWindows -batch "cd('$matlabRepo'); addpath('matlab'); plot_primary_results('results/$report'); verify_primary_results('results/$report');"
    if ($LASTEXITCODE -ne 0) { throw 'MATLAB plotting failed' }
    if ($IncludeSecondary) {
        & $MatlabExe -wait -nojvm -noFigureWindows -batch "cd('$matlabRepo'); addpath('matlab'); plot_model_comparison('results/model_comparison');"
        if ($LASTEXITCODE -ne 0) { throw 'MATLAB model comparison plotting failed' }
    }
} else {
    throw 'MATLAB executable not found. Validated data is ready; supply -MatlabExe to export the figures.'
}
