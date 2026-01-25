param(
    [string]$HostUrl = "http://127.0.0.1:8000/healthz",
    [int]$TimeoutSeconds = 120
)

Write-Host "Starting Django dev server..."
$server = Start-Process -FilePath python -ArgumentList "manage.py runserver 127.0.0.1:8000" -PassThru

Write-Host "Waiting for healthz at $HostUrl"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-WebRequest -Uri $HostUrl -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            Write-Host "Server is ready." -ForegroundColor Green
            Write-Host "PID: $($server.Id)"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

Write-Host "Server did not become ready in time." -ForegroundColor Red
# Attempt to stop
try { Stop-Process -Id $server.Id -Force } catch {}
exit 1
