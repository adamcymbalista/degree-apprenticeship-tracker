@echo off
cd /d "%~dp0"

echo ===== git status (before) ===== > push_update2_log.txt
git status >> push_update2_log.txt 2>&1

echo. >> push_update2_log.txt
echo ===== staging all changes ===== >> push_update2_log.txt
git add -A >> push_update2_log.txt 2>&1

echo. >> push_update2_log.txt
echo ===== committing (if there is anything new staged) ===== >> push_update2_log.txt
git diff --cached --quiet
if errorlevel 1 (
    git commit -F commit_msg3.txt >> push_update2_log.txt 2>&1
) else (
    echo Nothing new to commit >> push_update2_log.txt
)

echo. >> push_update2_log.txt
echo ===== pulling any remote changes first ===== >> push_update2_log.txt
git pull --rebase origin main >> push_update2_log.txt 2>&1

echo. >> push_update2_log.txt
echo ===== pushing ===== >> push_update2_log.txt
git push >> push_update2_log.txt 2>&1

echo. >> push_update2_log.txt
echo ===== DONE ===== >> push_update2_log.txt

del commit_msg3.txt 2>nul

type push_update2_log.txt
echo.
echo Finished. Full output saved to push_update2_log.txt - this window will stay open, press any key to close.
pause >nul
