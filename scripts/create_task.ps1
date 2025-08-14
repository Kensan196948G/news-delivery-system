# News Delivery System - Windows Task Scheduler Setup
# ニュース配信システム - Windows タスクスケジューラ設定

param(
    [string]$PythonPath = "python",
    [string]$ProjectPath = (Get-Location).Path,
    [string]$UserName = $env:USERNAME
)

Write-Host "========================================" -ForegroundColor Blue
Write-Host "News Delivery System Task Scheduler Setup" -ForegroundColor Blue
Write-Host "ニュース配信システム タスクスケジューラ設定" -ForegroundColor Blue  
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Check if running as Administrator
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   Some operations may require elevated privileges" -ForegroundColor Yellow
    Write-Host ""
}

# Validate paths
$mainScript = Join-Path $ProjectPath "src\main.py"
if (-not (Test-Path $mainScript)) {
    Write-Host "❌ Error: main.py not found at $mainScript" -ForegroundColor Red
    exit 1
}

Write-Host "📍 Project Path: $ProjectPath" -ForegroundColor Green
Write-Host "🐍 Python Path: $PythonPath" -ForegroundColor Green
Write-Host "👤 User: $UserName" -ForegroundColor Green
Write-Host ""

try {
    # Test Python installation
    Write-Host "🔍 Testing Python installation..." -ForegroundColor Cyan
    $pythonVersion = & $PythonPath --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found at '$PythonPath'"
    }
    Write-Host "✅ $pythonVersion" -ForegroundColor Green

    # Create scheduled tasks
    Write-Host "📅 Creating scheduled tasks..." -ForegroundColor Cyan

    # Task settings
    $taskSettings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 5)

    # Principal (user context)
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId $UserName -LogonType Interactive

    # Daily news collection tasks - 日次ニュース収集タスク
    $dailyTimes = @("07:00", "12:00", "18:00")
    
    foreach ($time in $dailyTimes) {
        $taskName = "NewsDelivery-Daily-$($time.Replace(':', ''))"
        
        # Create trigger for specific time
        $trigger = New-ScheduledTaskTrigger -Daily -At $time
        
        # Create action
        $action = New-ScheduledTaskAction `
            -Execute $PythonPath `
            -Argument "`"$mainScript`" --mode daily" `
            -WorkingDirectory $ProjectPath
        
        # Register task
        Register-ScheduledTask `
            -TaskName $taskName `
            -Trigger $trigger `
            -Action $action `
            -Principal $taskPrincipal `
            -Settings $taskSettings `
            -Description "ニュース配信システム - 日次実行 ($time)" `
            -Force | Out-Null
        
        Write-Host "   ✅ Created: $taskName" -ForegroundColor Green
    }

    # Emergency check task - 緊急チェックタスク (every 2 hours)
    $emergencyTaskName = "NewsDelivery-Emergency-Check"
    
    # Create trigger for every 2 hours
    $emergencyTrigger = New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 365)
    
    # Create action for emergency check
    $emergencyAction = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument "`"$mainScript`" --mode emergency" `
        -WorkingDirectory $ProjectPath
    
    # Register emergency task
    Register-ScheduledTask `
        -TaskName $emergencyTaskName `
        -Trigger $emergencyTrigger `
        -Action $emergencyAction `
        -Principal $taskPrincipal `
        -Settings $taskSettings `
        -Description "ニュース配信システム - 緊急チェック (2時間毎)" `
        -Force | Out-Null
    
    Write-Host "   ✅ Created: $emergencyTaskName" -ForegroundColor Green

    # Weekly summary task - 週次サマリータスク (Sunday 20:00)
    $weeklyTaskName = "NewsDelivery-Weekly-Summary"
    
    # Create trigger for Sunday 20:00
    $weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "20:00"
    
    # Create action for weekly summary
    $weeklyAction = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument "`"$mainScript`" --mode weekly" `
        -WorkingDirectory $ProjectPath
    
    # Register weekly task
    Register-ScheduledTask `
        -TaskName $weeklyTaskName `
        -Trigger $weeklyTrigger `
        -Action $weeklyAction `
        -Principal $taskPrincipal `
        -Settings $taskSettings `
        -Description "ニュース配信システム - 週次サマリー (日曜 20:00)" `
        -Force | Out-Null
    
    Write-Host "   ✅ Created: $weeklyTaskName" -ForegroundColor Green

    Write-Host ""
    Write-Host "🎉 Task Scheduler setup completed successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Display created tasks
    Write-Host "📋 Created Tasks:" -ForegroundColor Cyan
    $createdTasks = @(
        "NewsDelivery-Daily-0700",
        "NewsDelivery-Daily-1200", 
        "NewsDelivery-Daily-1800",
        "NewsDelivery-Emergency-Check",
        "NewsDelivery-Weekly-Summary"
    )
    
    foreach ($taskName in $createdTasks) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            $status = if ($task.State -eq "Ready") { "✅ Ready" } else { "⚠️  $($task.State)" }
            Write-Host "   $taskName : $status" -ForegroundColor White
        }
    }
    
    Write-Host ""
    Write-Host "📖 Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Test tasks manually:" -ForegroundColor White
    Write-Host "   Start-ScheduledTask -TaskName 'NewsDelivery-Daily-0700'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. View task history:" -ForegroundColor White
    Write-Host "   Get-ScheduledTask | Where-Object TaskName -like 'NewsDelivery-*'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Open Task Scheduler GUI:" -ForegroundColor White
    Write-Host "   taskschd.msc" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. View logs:" -ForegroundColor White
    Write-Host "   Check data/logs/ directory" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "❌ Error during task creation: $_" -ForegroundColor Red
    Write-Host ""
    
    # Show troubleshooting tips
    Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Run PowerShell as Administrator" -ForegroundColor White
    Write-Host "2. Check Python path: $PythonPath" -ForegroundColor White
    Write-Host "3. Verify project path: $ProjectPath" -ForegroundColor White
    Write-Host "4. Ensure main.py exists at: $mainScript" -ForegroundColor White
    
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")