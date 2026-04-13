# Load .env file into the current process environment
if (Test-Path "$PSScriptRoot\..\..\.env") {
    $envFile = "$PSScriptRoot\..\..\.env"
    Get-Content $envFile | Where-Object { $_ -match '^([^#=]+)=(.*)$' } | ForEach-Object {
        $varName = $matches[1].Trim()
        $varValue = $matches[2].Trim()
        [System.Environment]::SetEnvironmentVariable($varName, $varValue, "Process")
        Write-Host "Loaded: $varName"
    }
} else {
    Write-Host "Error: .env file not found in project root." -ForegroundColor Red
}
