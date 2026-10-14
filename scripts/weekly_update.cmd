@echo off
rem Run by the "FL Players site update" scheduled task every morning (daily since 2026-10-13).
rem Pulls first so edits made on GitHub are not overwritten, then refreshes and pushes.
cd /d "%~dp0.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs
echo ==== %date% %time% ==== >> logs\weekly_update.log
git checkout master >> logs\weekly_update.log 2>&1
git pull --rebase >> logs\weekly_update.log 2>&1
python scripts\update_site.py --push >> logs\weekly_update.log 2>&1
echo exit code %errorlevel% >> logs\weekly_update.log
