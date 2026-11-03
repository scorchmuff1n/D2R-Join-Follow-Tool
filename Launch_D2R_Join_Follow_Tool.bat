@echo off
title D2R Join/Follow Tool
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip show pyautogui >nul 2>nul
    if errorlevel 1 (
        echo Installing required package: pyautogui
        py -3 -m pip install pyautogui
        if errorlevel 1 (
            echo.
            echo Could not install pyautogui. Check your internet connection and Python installation.
            pause
            exit /b 1
        )
    )
    py -3 "%~dp0D2R_Join_Follow_Tool.py"
) else (
    python -m pip show pyautogui >nul 2>nul
    if errorlevel 1 (
        echo Installing required package: pyautogui
        python -m pip install pyautogui
        if errorlevel 1 (
            echo.
            echo Could not install pyautogui. Check your internet connection and Python installation.
            pause
            exit /b 1
        )
    )
    python "%~dp0D2R_Join_Follow_Tool.py"
)

if errorlevel 1 (
    echo.
    echo The tool exited with an error.
    pause
)
