@echo off
pushd "%~dp0" || (
	echo Failed to change directory.
	pause
	exit /b 1
)

py Hygieia-AI.py
popd
pause