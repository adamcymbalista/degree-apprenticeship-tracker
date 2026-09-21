@echo off
cd /d "%~dp0"

echo ===== git status (before) ===== > push_log.txt
git status >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== untracking venv if it was ever committed ===== >> push_log.txt
git rm -r --cached venv >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== staging all changes ===== >> push_log.txt
git add -A >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== git status (after staging) ===== >> push_log.txt
git status >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== committing ===== >> push_log.txt
git commit -F commit_msg.txt >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== setting remote ===== >> push_log.txt
git remote remove origin >> push_log.txt 2>&1
git remote add origin https://github.com/adamcymbalista/degree-apprenticeship-tracker.git >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== renaming branch to main ===== >> push_log.txt
git branch -M main >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== pushing (a browser window may open asking you to sign in to GitHub - sign in there if it does) ===== >> push_log.txt
git push -u origin main >> push_log.txt 2>&1

echo. >> push_log.txt
echo ===== DONE ===== >> push_log.txt

del commit_msg.txt

type push_log.txt
echo.
echo Finished. Full output saved to push_log.txt - this window will stay open, press any key to close.
pause >nul
