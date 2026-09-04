@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 滇西北攻略 - 一键更新到GitHub

set PY=F:\.workbuddy\binaries\python\versions\3.13.12\python.exe
if exist "%PY%" goto run

set PY=python
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   [错误] 找不到 Python。
  echo   请先安装 Python 后重试。
  echo.
  pause
  exit /b 1
)

:run
"%PY%" "%~dp0上传更新.py"
