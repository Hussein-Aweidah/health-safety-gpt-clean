@echo off
REM Script to clean Python project cache files before distribution (Windows)
REM Run this before sharing your project with others or deploying

echo.
echo =====================================
echo Cleaning Python project cache files
echo =====================================
echo.

REM Remove Python cache directories
echo Removing Python __pycache__ directories...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo Removing compiled Python files...
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul

REM Remove IDE files
echo Removing IDE configuration files...
if exist .vs rmdir /s /q .vs
if exist .vscode rmdir /s /q .vscode
if exist .idea rmdir /s /q .idea
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .mypy_cache rmdir /s /q .mypy_cache

REM Remove Windows-specific files
echo Removing Windows cache files...
del /s /q Thumbs.db 2>nul
del /s /q desktop.ini 2>nul
del /s /q *.lnk 2>nul

REM Remove Mac/Linux files (if any)
echo Removing Mac/Linux cache files...
del /s /q .DS_Store 2>nul
del /s /q ._* 2>nul
del /s /q *.swp 2>nul
del /s /q *.swo 2>nul
del /s /q "*~" 2>nul

REM Remove editor backup files
echo Removing editor backup files...
del /s /q *.bak 2>nul
del /s /q *.tmp 2>nul
del /s /q *.log 2>nul

echo.
echo =====================================
echo Cleanup complete!
echo =====================================
echo.
echo Files that have been removed:
echo   - Python __pycache__ directories
echo   - Compiled .pyc, .pyo, .pyd files
echo   - IDE config folders (.vs, .vscode, .idea)
echo   - Windows files: Thumbs.db, desktop.ini
echo   - Mac/Linux files: .DS_Store, swap files
echo   - Editor backups: *.bak, *.tmp, *.log
echo.
echo Optional: Consider removing these before distribution:
echo   - chroma_db/ (ChromaDB data)
echo   - chromadb/ (ChromaDB data)
echo   - user_data/ (User-specific data)
echo   - faiss_index/ (Unless pre-built index needed)
echo.
echo Windows -^> Mac/Linux Notes:
echo   - All platform-specific cache files have been removed
echo   - Python bytecode will be regenerated on target platform
echo   - Indexes can be rebuilt: python build_faiss_index.py
echo.
pause

