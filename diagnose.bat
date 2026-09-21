@echo off
cd /d "C:\Users\adamc\Downloads\degree-apprenticeship-tracker\degree-apprenticeship-tracker"
venv\Scripts\python.exe diagnose.py > diagnose_log.txt 2>&1
