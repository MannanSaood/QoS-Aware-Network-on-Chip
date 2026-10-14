param(
    [ValidateRange(1,8)][int]$Jobs = 2,
    [string]$Distro = 'Ubuntu-24.04',
    [string]$Matlab = 'C:/Program Files/MATLAB/R2026b/bin/matlab.exe',
    [switch]$PlotOnly
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$normalizedPath = $projectPath.Replace('\','/')
if ($normalizedPath -notmatch '^[A-Za-z]:/') { throw 'Expected a local Windows drive path.' }
$linuxProjectPath = '/mnt/' + $normalizedPath.Substring(0,1).ToLowerInvariant() + $normalizedPath.Substring(2)
function Invoke-ProjectPython([string[]]$PythonArgs) {
    & wsl -d $Distro --cd $linuxProjectPath -- python3 @PythonArgs
    if ($LASTEXITCODE -ne 0) { throw "Python stage failed: $($PythonArgs -join ' ')" }
}
if (-not $PlotOnly) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectPath 'results/qos_comparison/protocol.json'))) {
        Invoke-ProjectPython @('scripts/setup_qos.py','--jobs','2')
        Invoke-ProjectPython @('scripts/validate_qos.py')
        Invoke-ProjectPython @('scripts/check_fr_coverage.py')
    }
    # Resume requires unchanged frozen binary/source/validation hashes.
    # Do not invoke a second copy while an existing sweep is active.
    Invoke-ProjectPython @('scripts/run_qos_grid.py','--jobs',"$Jobs")
}
Invoke-ProjectPython @('scripts/prepare_qos_results.py')
$matlabProjectPath = $normalizedPath.Replace("'","''")
$batchCommand = "cd('$matlabProjectPath'); addpath('matlab'); plot_primary_results('results/qos_report'); verify_primary_results('results/qos_report');"
$logPath = Join-Path $projectPath 'results/qos_report/matlab_export.log'
& $Matlab -wait -nojvm -noFigureWindows -logfile $logPath -batch $batchCommand
if ($LASTEXITCODE -ne 0) { throw 'MATLAB export or figure verification failed.' }
Write-Output 'QoS measurements and verified MATLAB figures complete. No presentation was modified.'
