@echo off
setlocal EnableDelayedExpansion
title JosTEL Moodle Bare-Metal Machine Restore Helper (Windows)
color 0b

echo =========================================================================
echo       JosTEL Moodle Bare-Metal Machine Restore Helper (Windows / XAMPP)
echo                 St. Joseph's College (Autonomous), Tiruchirappalli
echo =========================================================================
echo.
echo This script will help you restore your Moodle Database, code, and moodledata
echo onto this machine.
echo.

:: 1. Check MySQL / MariaDB Availability
where mysql >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\xampp\mysql\bin\mysql.exe" (
        set "PATH=C:\xampp\mysql\bin;!PATH!"
        echo [*] Detected XAMPP MySQL in C:\xampp\mysql\bin. Added to PATH.
    ) else (
        echo [!] WARNING: 'mysql' command not found in your system PATH.
        echo     If using XAMPP, ensure MySQL is running in XAMPP Control Panel.
        echo.
    )
)

:: 2. Prompt for Database Settings
set /p DB_HOST="Enter Database Host [default: 127.0.0.1]: "
if "!DB_HOST!"=="" set DB_HOST=127.0.0.1

set /p DB_USER="Enter Database User [default: root]: "
if "!DB_USER!"=="" set DB_USER=root

set /p DB_PASS="Enter Database Password (leave blank if none): "

set /p DB_NAME="Enter Target Database Name [default: moodle]: "
if "!DB_NAME!"=="" set DB_NAME=moodle

set /p SQL_FILE="Enter Path to Moodle SQL dump file (.sql or .sql.gz): "
if "!SQL_FILE!"=="" (
    echo [!] No SQL file specified. Exiting.
    pause
    exit /b 1
)

if not exist "!SQL_FILE!" (
    echo [!] File not found: !SQL_FILE!
    pause
    exit /b 1
)

:: 3. Handle .sql.gz decompression if needed
set "IMPORT_SQL=!SQL_FILE!"
if /i "!SQL_FILE:~-3!"==".gz" (
    echo [*] Detected gzip compressed dump. Decompressing...
    where tar >nul 2>nul
    if %errorlevel% equ 0 (
        tar -xzf "!SQL_FILE!"
        set "IMPORT_SQL=!SQL_FILE:~0,-3!"
    ) else (
        echo [!] Please extract !SQL_FILE! to plain .sql first using 7-Zip.
        pause
        exit /b 1
    )
)

:: 4. Build Password Parameter
set "PASS_PARAM="
if not "!DB_PASS!"=="" set "PASS_PARAM=-p!DB_PASS!"

echo.
echo =========================================================================
echo 1. Creating Database '!DB_NAME!' (utf8mb4_unicode_ci)...
echo =========================================================================
mysql -h !DB_HOST! -u !DB_USER! !PASS_PARAM! -e "CREATE DATABASE IF NOT EXISTS \`!DB_NAME!\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if %errorlevel% neq 0 (
    echo [!] Failed to create database. Please verify host, username and password.
    pause
    exit /b 1
)
echo [OK] Database created or verified.

echo.
echo =========================================================================
echo 2. Importing SQL dump into '!DB_NAME!'...
echo    (This may take a few minutes for large databases...)
echo =========================================================================
mysql -h !DB_HOST! -u !DB_USER! !PASS_PARAM! !DB_NAME! < "!IMPORT_SQL!"
if %errorlevel% neq 0 (
    echo [!] SQL Import failed.
    pause
    exit /b 1
)
echo [OK] Database import completed successfully!

echo.
echo =========================================================================
echo 3. Next Steps to Complete Restore on this Machine:
echo =========================================================================
echo A. Place Moodle code in your web root:
echo    e.g. C:\xampp\htdocs\moodle
echo.
echo B. Place 'moodledata' outside the web root:
echo    e.g. C:\xampp\moodledata
echo.
echo C. Edit config.php:
echo    $CFG->dbtype    = 'mariadb'; (or 'mysqli')
echo    $CFG->dbhost    = '!DB_HOST!';
echo    $CFG->dbname    = '!DB_NAME!';
echo    $CFG->dbuser    = '!DB_USER!';
echo    $CFG->dbpass    = '!DB_PASS!';
echo    $CFG->wwwroot   = 'http://localhost/moodle';
echo    $CFG->dataroot  = 'C:\\xampp\\moodledata';
echo.
echo D. Run URL replacement CLI to update the original domain to localhost:
echo    php C:\xampp\htdocs\moodle\admin\cli\replace.php ^
echo        --search=https://service.sjctni.edu/jostel/moodle ^
echo        --replace=http://localhost/moodle
echo.
echo E. Purge Moodle caches:
echo    php C:\xampp\htdocs\moodle\admin\cli\purge_caches.php
echo.
echo =========================================================================
echo [SUCCESS] Database restoration complete! Press any key to exit.
echo =========================================================================
pause
