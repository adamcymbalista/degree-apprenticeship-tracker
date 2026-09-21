@echo off
cd /d "%~dp0"

echo ===== git status (before) ===== > push_update_log.txt
git status >> push_update_log.txt 2>&1

echo. >> push_update_log.txt
echo ===== staging all changes ===== >> push_update_log.txt
git add -A >> push_update_log.txt 2>&1

echo. >> push_update_log.txt
echo ===== committing ===== >> push_update_log.txt
git commit -F commit_msg2.txt >> push_update_log.txt 2>&1

echo. >> push_update_log.txt
echo ===== pushing ===== >> push_update_log.txt
git push >> push_update_log.txt 2>&1

echo. >> push_update_log.txt
echo ===== DONE ===== >> push_update_log.txt

del commit_msg2.txt

type push_update_log.txt
echo.
echo Finished. Full output saved to push_update_log.txt - this window will stay open, press any key to close.
pause >nul
