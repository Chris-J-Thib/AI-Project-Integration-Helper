@echo off
setlocal EnableExtensions
chcp 65001 >nul
REM init_windows.cmd - Ensures a usable Python 3.8+ is present (installing
REM it if confirmed), then hands off to init.py for the rest of setup.

set "SCRIPT_DIR=%~dp0"
set "MIN_MAJOR=3"
set "MIN_MINOR=8"
set "PYTHON_BIN="

call :find_python
if defined PYTHON_BIN (
    echo Found usable Python: %PYTHON_BIN% (%PYTHON_VER%)
    goto :launch_init
)

echo No usable Python %MIN_MAJOR%.%MIN_MINOR%+ found (Python 2 or missing does not count).
echo This project's AI tooling requires Python %MIN_MAJOR%.%MIN_MINOR%+ to build and maintain its index.
echo.

call :detect_pkg_manager

:menu
if defined PM (
    echo Options: [i]nstall using %PM%, [m]ore info, [q]uit
) else (
    echo Options: [m]ore info, [q]uit
)
set /p "CHOICE=> "
if /i "%CHOICE%"=="i" goto :do_install
if /i "%CHOICE%"=="m" goto :do_info
if /i "%CHOICE%"=="q" goto :do_quit
echo Please enter i, m, or q.
goto :menu

:do_install
if not defined PM (
    echo No supported package manager detected; ignoring.
    goto :menu
)
call :install_cmd_for
echo This will run: %INSTALL_CMD%
set /p "CONFIRM=Proceed? [y/n] > "
if /i not "%CONFIRM%"=="y" goto :menu
call %INSTALL_CMD%
set "PYTHON_BIN="
call :find_python
if defined PYTHON_BIN (
    echo Installed successfully: %PYTHON_BIN%
    goto :launch_init
) else (
    echo Install ran but no usable Python %MIN_MAJOR%.%MIN_MINOR%+ was found afterward.
    exit /b 1
)

:do_info
echo.
echo Why Python is needed:
echo   This toolkit uses a Python script (generate_index.py) to scan the
echo   project and build/update .ai\manifests\index.json. That index is
echo   how an AI assistant quickly understands the project's structure
echo   without re-reading every file each session.
echo.
echo   The script also merges updates - it keeps existing file/folder
echo   descriptions and only adds or removes entries when files actually
echo   change, so context isn't lost between sessions.
echo.
echo   Python was chosen because it handles this reliably (correct JSON
echo   output, Unicode filenames, etc.) on both Linux and Windows, unlike
echo   plain shell/batch scripts.
echo.
goto :menu

:do_quit
echo Aborted. No dependencies were installed.
exit /b 1

:launch_init
call %PYTHON_BIN% "%SCRIPT_DIR%init.py"
exit /b %errorlevel%

:find_python
for %%C in (python py) do (
    if not defined PYTHON_BIN (
        where %%C >nul 2>&1
        if not errorlevel 1 (
            set "CANDIDATE=%%C"
            if /i "%%C"=="py" set "CANDIDATE=py -3"
            call :check_candidate
        )
    )
)
exit /b 0

:check_candidate
for /f "delims=" %%V in ('%CANDIDATE% -c "import sys; print(\"%%d.%%d\" %% sys.version_info[:2])" 2^>nul') do set "VER=%%V"
if not defined VER exit /b 0
for /f "tokens=1,2 delims=." %%A in ("%VER%") do (
    set "MAJOR=%%A"
    set "MINOR=%%B"
)
if not "%MAJOR%"=="%MIN_MAJOR%" (set "VER=" & exit /b 0)
if %MINOR% lss %MIN_MINOR% (set "VER=" & exit /b 0)
set "PYTHON_BIN=%CANDIDATE%"
set "PYTHON_VER=%VER%"
set "VER="
exit /b 0

:detect_pkg_manager
set "PM="
where winget >nul 2>&1
if not errorlevel 1 (set "PM=winget" & exit /b 0)
where choco >nul 2>&1
if not errorlevel 1 (set "PM=choco" & exit /b 0)
exit /b 0

:install_cmd_for
if "%PM%"=="winget" set "INSTALL_CMD=winget install -e --id Python.Python.3.12"
if "%PM%"=="choco" set "INSTALL_CMD=choco install -y python3"
exit /b 0
