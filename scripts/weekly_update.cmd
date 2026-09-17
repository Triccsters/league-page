@echo off
rem Run by the "FL Players site update" scheduled task every Tuesday morning.
rem Pulls first so edits made on GitHub are not overwritten, then refreshes and pushes.
cd /d "%~dp0.."
if not exist logs mkdir logs
echo ==== %date% %time% ==== >> logs\weekly_update.log
git checkout master >> logs\weekly_update.log 2>&1
git pull --rebase >> logs\weekly_update.log 2>&1
python scripts\update_site.py --push >> logs\weekly_update.log 2>&1
echo exit code %errorlevel% >> logs\weekly_update.log
