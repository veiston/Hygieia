@echo off
pushd "C:\Users\veikk\Documents\GitHub\Hygieia" || (
	echo Failed to change directory.
	pause
	exit /b 1
)
py Hygieia_AI.py
popd
pause