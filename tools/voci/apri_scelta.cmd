@echo off
rem SPDX-FileCopyrightText: 2026 Luigi Massari
rem SPDX-License-Identifier: MIT
rem La pagina per scegliere le voci: avvia il server locale e apre il browser. Ctrl+C per fermare.
setlocal
if "%CAR_LAB%"=="" set "CAR_LAB=%USERPROFILE%\ctrlaltrevenge-lab"
start "" http://127.0.0.1:8765/
"%CAR_LAB%\tts\venv-qwen3\Scripts\python.exe" -I "%~dp0scelta_server.py"
