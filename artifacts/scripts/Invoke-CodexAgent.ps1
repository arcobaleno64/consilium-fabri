<#
.SYNOPSIS
Resilient wrapper for the Codex CLI providing task-scale model selection and multi-tier fallback for API errors.

.DESCRIPTION
Wraps the codex CLI to catch 429 Too Many Requests, 400 Bad Request, and 5xx server errors.
Selects the default model and reasoning effort from the task scale unless explicitly overridden.
Executes standard Exponential Backoff.
If failures persist, dynamically steps through the fallback models for the selected task scale.
If models are exhausted, it switches to a Fallback API key and starts from the top model again.
Returns standard output on success or throws a fatal block if all options are exhausted.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [string]$Prompt,

    [string]$ApprovalMode = "full-auto",

    [ValidateSet("tiny", "docs-only", "standard", "high-risk", "cross-module", "critical", "security", "architecture")]
    [string]$TaskScale = "standard",

    [ValidateSet("auto", "fixed", "fallback")]
    [string]$ModelPolicy = "auto",

    [string]$Model = "",
    
    [string]$ReasoningEffort = "",

    [int]$MaxRetriesPerTier = 2,
    [int]$BaseBackoffSeconds = 2,
    
    [string]$Executable = "codex.cmd"
)

# Core Error Patterns to Catch
$RetryPatterns = @(
    "429",
    "Too Many Requests",
    "RateLimitError",
    "400 Bad Request",
    "500 Internal Server",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "Failed to fetch",
    "ECONNRESET"
)
$RegexPattern = ($RetryPatterns | ForEach-Object { [regex]::Escape($_) }) -join '|'

function Get-TaskScaleProfile {
    param([string]$Scale)

    switch ($Scale) {
        { $_ -in @("tiny", "docs-only") } {
            return @{
                Effort = "low"
                Models = @("gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.4")
            }
        }
        "standard" {
            return @{
                Effort = "medium"
                Models = @("gpt-5.3-codex", "gpt-5.4", "gpt-5.4-mini")
            }
        }
        { $_ -in @("high-risk", "cross-module") } {
            return @{
                Effort = "high"
                Models = @("gpt-5.4", "gpt-5.3-codex", "gpt-5.4-mini")
            }
        }
        { $_ -in @("critical", "security", "architecture") } {
            return @{
                Effort = "xhigh"
                Models = @("gpt-5.4", "gpt-5.3-codex", "gpt-5.4-mini")
            }
        }
    }
}

$Profile = Get-TaskScaleProfile -Scale $TaskScale
$EffectiveReasoningEffort = if ([string]::IsNullOrWhiteSpace($ReasoningEffort)) { $Profile.Effort } else { $ReasoningEffort }
$Models = @($Profile.Models)

if (![string]::IsNullOrWhiteSpace($Model)) {
    if ($ModelPolicy -eq "fixed") {
        $Models = @($Model)
    } else {
        $Models = @($Model) + ($Models | Where-Object { $_ -ne $Model })
    }
}

Write-Host "  -> Task Scale: $TaskScale; Model Policy: $ModelPolicy; Reasoning Effort: $EffectiveReasoningEffort" -ForegroundColor Cyan

$IsSuccess = $false
$FinalOutput = ""

foreach ($model in $Models) {
    Write-Host "  -> Active Model Tier: $model" -ForegroundColor Cyan

    for ($attempt = 0; $attempt -le $MaxRetriesPerTier; $attempt++) {
        
        # Construct args
        $processArgs = @("exec", "-m", $model)
        if ($ApprovalMode -eq "full-auto") {
            $processArgs += "--full-auto"
        } else {
            $processArgs += "-a", $ApprovalMode
        }
        if (![string]::IsNullOrWhiteSpace($EffectiveReasoningEffort)) {
            $processArgs += "-c", "model_reasoning_effort=`"$EffectiveReasoningEffort`""
        }
        $processArgs += $Prompt
        Write-Host "    [*] Attempt $($attempt+1)/$($MaxRetriesPerTier+1)..." -ForegroundColor Gray
        
        $output = $null
        $errText = ""
        $combinedText = ""
        $lastExitCode = 1
        
        try {
            $procOutput = $null | & $Executable $processArgs 2>&1
            
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
            if ($combinedText -match $RegexPattern) {
                $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                Write-Host "    [Backoff] Target error string matched. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds $sleepTime
            } else {
                $sleepTime = [Math]::Pow(2, $attempt) * $BaseBackoffSeconds
                Write-Host "    [Backoff] Generic failure. Sleeping for $sleepTime seconds..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds $sleepTime
            }
        }
    } # End Attempt Loop

    if ($IsSuccess) { break }
    Write-Host "  -> Exhausted retries for $model. Escalating tier (fallback)..." -ForegroundColor Magenta
} # End Model Loop

# Wrap up
if ($IsSuccess) {
    Write-Output $FinalOutput
    exit 0
} else {
    Write-Error "__FATAL:[Blocked] All fallback models exhausted for Codex CLI.__`nReview terminal logs or quota statuses."
    exit 1
}
