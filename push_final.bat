@echo off
cd /d "%~dp0"
set LOG=push_final.log

echo ===== git status (before) ===== > %LOG%
git status >> %LOG% 2>&1

echo. >> %LOG%
echo ===== staging all changes ===== >> %LOG%
git add -A >> %LOG% 2>&1

echo. >> %LOG%
echo ===== committing (if there is anything new staged) ===== >> %LOG%
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Add manual mode picker to the daily workflow, make db-commit step resilient to races" -m "Lets Run workflow in the Actions tab choose daily / weekly / test-email instead of always running --daily. Also pulls before pushing in the commit-database step so an overlapping run no longer fails with a rejected push." -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_017DBdQkJwGf1sSVctJZkGXE" >> %LOG% 2>&1
) else (
    echo Nothing new to commit >> %LOG%
)

echo. >> %LOG%
echo ===== pulling any remote changes first ===== >> %LOG%
git pull --rebase origin main >> %LOG% 2>&1

echo. >> %LOG%
echo ===== pushing ===== >> %LOG%
git push >> %LOG% 2>&1

echo. >> %LOG%
echo ===== DONE ===== >> %LOG%

type %LOG%
echo.
echo Finished. Full output saved to %LOG% - this window will stay open, press any key to close.
pause >nul
