param(
    [Parameter(Position = 0)]
    [ValidateSet("list", "setup", "run")]
    [string]$Command = "list",

    [Parameter(Position = 1)]
    [string]$Scenario = "all",

    [ValidateSet("success", "abort")]
    [string]$Mode = "success"
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Script = Join-Path $RepoRoot "tests\support\phase7_uat_envs.py"
$OutputRoot = Join-Path $RepoRoot "tests\uat\phase7\envs"

if ($Command -eq "run") {
    & $Python $Script run $Scenario --output-root $OutputRoot --mode $Mode
    exit $LASTEXITCODE
}

if ($Command -eq "setup") {
    & $Python $Script setup $Scenario --output-root $OutputRoot
    exit $LASTEXITCODE
}

& $Python $Script list --output-root $OutputRoot
exit $LASTEXITCODE
