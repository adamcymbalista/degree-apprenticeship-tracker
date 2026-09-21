@echo off
cd /d "%~dp0"
set LOG=push_apprentifinder.log

echo ===== running tests first ===== > %LOG%
venv\Scripts\python.exe -m unittest discover -s tests >> %LOG% 2>&1
set TESTS_OK=%errorlevel%

if not "%TESTS_OK%"=="0" (
    echo. >> %LOG%
    echo ===== TESTS FAILED - not committing or pushing, see output above ===== >> %LOG%
    goto :show
)

echo. >> %LOG%
echo ===== tests passed ===== >> %LOG%

echo. >> %LOG%
echo ===== git status (before) ===== >> %LOG%
git status >> %LOG% 2>&1

echo. >> %LOG%
echo ===== staging all changes ===== >> %LOG%
git add -A >> %LOG% 2>&1

echo. >> %LOG%
echo ===== committing (if there is anything new staged) ===== >> %LOG%
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Add apprentifinder.co.uk as a source, fix QMUL URL, add QMUL-partner scoring boost" -m "apprentifinder.co.uk aggregates listings from many employer/university sites rather than depending on what an employer chooses to advertise on the government site. Its /browse page is client-rendered, but it calls a plain unauthenticated JSON endpoint (api/opportunities) which this scrapes instead - robots.txt allows everything." -m "QMUL's own site was confirmed to be pure course-info prose, not a vacancy feed, regardless of URL - fixed the URL for accuracy but the real fix is scoring.py now boosting any listing whose training-provider field mentions Queen Mary, since apprentifinder's feed exposes that field and findapprenticeship's search results don't." -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_017DBdQkJwGf1sSVctJZkGXE" >> %LOG% 2>&1
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

:show
type %LOG%
echo.
echo Finished. Full output saved to %LOG% - this window will stay open, press any key to close.
pause >nul
