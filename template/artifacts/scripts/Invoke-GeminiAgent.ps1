<#
.SYNOPSIS
Resilient wrapper for the Gemini CLI providing multi-tier fallback for API errors.

.DESCRIPTION
Wraps the gemini CLI to catch 429 MODEL_CAPACITY_EXHAUSTED, 400 Bad Request, and 5xx server errors.
Executes standard Exponential Backoff.
If failures persist, dynamically steps up through fallback models (flash -> pro).
If models are exhausted, it switches to a Fallback API key and starts from the bottom model again.
Returns standard output on success or throws a fatal block if all options are exhausted.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$Prompt,

    [string]$Profile = $null,
    [string]$ApprovalMode = "yolo",
    
    [int]$MaxRetriesPerTier = 2,
    [int]$BaseBackoffSeconds = 2,
    
    [string]$Executable = "gemini.cmd"
)

# Core Error Patterns to Catch
$RetryPatterns = @(
    "429",
    "MODEL_CAPACITY_EXHAUSTED",
    "400 Bad Request",
    "500 Internal Server",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "Failed to fetch",
    "ECONNRESET"
)
$RegexPattern = ($RetryPatterns | ForEach-Object { [regex]::Escape($_) }) -join '|'

# Models Progression
$Models = @(
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview"
)

# Keys Progression
$OriginalKey = $env:GEMINI_API_KEY
$FallbackKey = $env:GEMINI_FALLBACK_API_KEY

$KeysToTry = @()
if (![string]::IsNullOrWhiteSpace($OriginalKey)) { $KeysToTry += $OriginalKey }
if (![string]::IsNullOrWhiteSpace($FallbackKey) -and $FallbackKey -ne $OriginalKey) { $KeysToTry += $FallbackKey }

if ($KeysToTry.Count -eq 0) {
    Write-Error "__FATAL:[Blocked] No API keys provided. Set GEMINI_API_KEY environment variable.__"
    exit 1
}

$IsSuccess = $false
$FinalOutput = ""

foreach ($keyIndex in 0..($KeysToTry.Count - 1)) {
    # Swap API Key in Env
    $env:GEMINI_API_KEY = $KeysToTry[$keyIndex]
    
    $KeyLabel = if ($keyIndex -eq 0) { "Primary Key" } else { "Fallback Key" }
    Write-Host "[Info] Harness engaging with $KeyLabel..." -ForegroundColor Cyan

    foreach ($model in $Models) {
        Write-Host "  -> Active Model Tier: $model" -ForegroundColor Cyan

        for ($attempt = 0; $attempt -le $MaxRetriesPerTier; $attempt++) {
            
            # Construct args
            $processArgs = @("-m", $model, "--approval-mode", $ApprovalMode)
            if (![string]::IsNullOrWhiteSpace($Profile)) {
                $processArgs += "--profile", $Profile
            }
            $processArgs += "-p", $Prompt

            Write-Host "    [*] Attempt $($attempt+1)/$($MaxRetriesPerTier+1)..." -ForegroundColor Gray
            
            $output = $null
            $errText = ""
            $combinedText = ""
            $lastExitCode = 1
            
            try {
                $procOutput = & $Executable $processArgs 2>&1
                
                $stdOutLines = @()
                $stdErrLines = @()
                foreach ($line in $procOutput) {
                    if ($line -is [System.Management.Automation.ErrorRecord]) {
                        $stdErrLines += $line.Exception.Message
                    } else {
                        $stdOutLines += $line
                    }
                }
                
                $outText = $stdOutLines -join "`n"
                $errText = $stdErrLines -join "`n"
                $lastExitCode = $LASTEXITCODE

                $combinedText = "$outText`n$errText"
                
                # Check outcome
                if ($lastExitCode -eq 0 -and -not ($combinedText -match $RegexPattern)) {
                    $IsSuccess = $true
                    $FinalOutput = $outText
                    break
                } else {
                    Write-Host "    [!] Intercepted API/Execution Error (ExitCode: $lastExitCode)" -ForegroundColor Yellow
                }

            } catch {
                Write-Host "    [!] Process Exception Caught: $($_.Exception.Message)" -ForegroundColor Red
                $combinedText = $_.Exception.Message
            }

            # Calculate backoff if not last attempt
            if ($attempt -lt $MaxRetriesPerTier) {
                # Check if it was one of our specific retry patterns
                if ($combinedText -match $RegexPattern) {
                    $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                    Write-Host "    [Backoff] Target error string matched. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                    Start-Sleep -Seconds $sleepTime
                } else {
                    # If it's some other fatal error that we don't recognize, do we still back off?
                    # Yes, per user request, we enter the loop.
                    $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                    Write-Host "    [Backoff] Generic failure. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                    Start-Sleep -Seconds $sleepTime
                }
            }
        } # End Attempt Loop

        if ($IsSuccess) { break }
        Write-Host "  -> Exhausted retries for $model. Escalating tier..." -ForegroundColor Magenta
    } # End Model Loop

    if ($IsSuccess) { break }
    if ($keyIndex -lt ($KeysToTry.Count - 1)) {
        Write-Host "[Alert] Exhausted all models on Primary Key. Swapping to Secondary API Key and resetting tiers..." -ForegroundColor Red
    }
} # End Key Loop

# Restore original key
$env:GEMINI_API_KEY = $OriginalKey

# Wrap up
if ($IsSuccess) {
    Write-Output $FinalOutput
    exit 0
} else {
    Write-Error "__FATAL:[Blocked] All fallback models and keys exhausted for Gemini CLI.__`nReview terminal logs or quota statuses."
    exit 1
}
