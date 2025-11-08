# Test script for queuectl
# Run with: .\venv\Scripts\Activate.ps1; .\test_commands.ps1

Write-Host "=== Testing queuectl ===" -ForegroundColor Green

Write-Host "`n1. Enqueue a successful job" -ForegroundColor Yellow
python queuectl.py enqueue '{"id":"job1","command":"echo Hello World"}'

Write-Host "`n2. Enqueue a failing job" -ForegroundColor Yellow
python queuectl.py enqueue '{"id":"job2","command":"cmd /c exit 1","max_retries":2}'

Write-Host "`n3. Check status" -ForegroundColor Yellow
python queuectl.py status

Write-Host "`n4. List pending jobs" -ForegroundColor Yellow
python queuectl.py list --state pending

Write-Host "`n5. Start workers (will run for 10 seconds)" -ForegroundColor Yellow
$proc = Start-Process python -ArgumentList "queuectl.py","worker","start","--count","2" -PassThru -NoNewWindow
Start-Sleep -Seconds 10
Stop-Process -Id $proc.Id -Force

Write-Host "`n6. Check status after processing" -ForegroundColor Yellow
python queuectl.py status

Write-Host "`n7. List DLQ jobs" -ForegroundColor Yellow
python queuectl.py dlq list

Write-Host "`n8. Test config" -ForegroundColor Yellow
python queuectl.py config set max-retries 5
python queuectl.py config get max-retries

Write-Host "`n=== Tests complete ===" -ForegroundColor Green

