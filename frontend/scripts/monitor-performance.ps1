# Mobile Performance Monitoring Script
# Usage: .\scripts\monitor-performance.ps1

Write-Host "=== SafeT Mobile Performance Monitor ===" -ForegroundColor Cyan
Write-Host ""

# Check if adb is available
$adbPath = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbPath) {
    Write-Host "ERROR: adb not found in PATH" -ForegroundColor Red
    Write-Host "Please ensure Android SDK platform-tools is in your PATH"
    exit 1
}

# Check if device/emulator is connected
$devices = adb devices | Select-String "device$"
if ($devices.Count -eq 0) {
    Write-Host "ERROR: No Android device/emulator connected" -ForegroundColor Red
    Write-Host "Please start an emulator or connect a device"
    exit 1
}

Write-Host "Connected devices:" -ForegroundColor Green
adb devices
Write-Host ""

# Menu
Write-Host "Select monitoring option:" -ForegroundColor Yellow
Write-Host "1. Monitor app startup (Displayed time)"
Write-Host "2. Monitor WebView console logs"
Write-Host "3. Monitor memory usage"
Write-Host "4. Monitor all (combined)"
Write-Host "5. Clear logcat and start fresh"
Write-Host "6. Exit"
Write-Host ""

$choice = Read-Host "Enter choice (1-6)"

switch ($choice) {
    "1" {
        Write-Host "`nMonitoring app startup times..." -ForegroundColor Cyan
        Write-Host "Launch the app now..." -ForegroundColor Yellow
        Write-Host ""
        adb logcat -c
        adb logcat | Select-String "Displayed"
    }
    "2" {
        Write-Host "`nMonitoring WebView console..." -ForegroundColor Cyan
        Write-Host ""
        adb logcat -c
        adb logcat | Select-String "chromium|Console|WebView"
    }
    "3" {
        Write-Host "`nMonitoring memory usage..." -ForegroundColor Cyan
        Write-Host "Getting memory stats for SafeT app..." -ForegroundColor Yellow
        Write-Host ""
        
        # Get package name
        $package = "io.ionic.starter"
        
        # Get PID
        $pid = adb shell "ps | grep $package" | ForEach-Object { ($_ -split '\s+')[1] }
        
        if ($pid) {
            Write-Host "App PID: $pid" -ForegroundColor Green
            Write-Host ""
            Write-Host "Memory stats:" -ForegroundColor Cyan
            adb shell dumpsys meminfo $package
        } else {
            Write-Host "App not running" -ForegroundColor Red
        }
    }
    "4" {
        Write-Host "`nMonitoring all events..." -ForegroundColor Cyan
        Write-Host ""
        adb logcat -c
        adb logcat | Select-String "Displayed|chromium|Console|WebView|ActivityManager"
    }
    "5" {
        Write-Host "`nClearing logcat..." -ForegroundColor Cyan
        adb logcat -c
        Write-Host "Logcat cleared!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Starting fresh monitoring..." -ForegroundColor Cyan
        adb logcat
    }
    "6" {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}
