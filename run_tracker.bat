@echo off
cd /d "C:\Users\adamc\Downloads\degree-apprenticeship-tracker\degree-apprenticeship-tracker"
venv\Scripts\python.exe -m app.main --daily >> tracker_log.txt 2>&1