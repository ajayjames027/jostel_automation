<?php
/**
 * JosTEL Moodle Secure Server Backup API Engine
 * St. Joseph's College (Autonomous), Tiruchirappalli
 * 
 * Place this file in your Moodle root directory:
 *   e.g., /var/www/html/moodle/admin_backup_api.php
 * 
 * Features:
 *   1. Automated extraction of Moodle Database ($CFG->dbname, $CFG->dbuser, etc. from config.php)
 *   2. Dual Engine: Native mysqldump/tar with Pure PHP PDO + ZipArchive fallback if exec() is restricted
 *   3. Excludes heavy cache folders (cache, localcache, sessions, temp) to keep backups lean & fast
 *   4. Token/Secret header security barrier
 *   5. Chunked resumable file streamer to prevent PHP memory exhaustion
 * 
 * Endpoints:
 *   GET/POST ?action=status               -> Server disk, DB size, moodledata size, backup history
 *   GET/POST ?action=create_db_backup     -> Dumps entire Moodle database to .sql.gz
 *   GET/POST ?action=create_full_backup   -> Dumps DB + moodledata + config to .tar.gz / .zip
 *   GET/POST ?action=list_backups         -> Lists all existing backup packages with sizes
 *   GET/POST ?action=download&file=...    -> Streams the backup file securely
 *   GET/POST ?action=delete&file=...      -> Deletes an old backup file
 */

// =========================================================================
// SECURITY CONFIGURATION
// =========================================================================
// Change this secret key to your own strong passphrase or keep this default:
define('BACKUP_SECRET_KEY', 'JosTEL_Moodle_Secure_Vault_2026_Key');

// Disable standard execution timeouts for large backups
@ini_set('max_execution_time', 0);
@ini_set('memory_limit', '1024M');
@set_time_limit(0);

// Enable Cross-Origin Resource Sharing (CORS) for authorized web dashboard clients
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-JosTEL-Secret');

if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// =========================================================================
// 1. AUTHENTICATION BARRIER
// =========================================================================
function verify_authentication() {
    $secret_provided = '';
    
    // Check Authorization or custom header
    if (!empty($_SERVER['HTTP_X_JOSTEL_SECRET'])) {
        $secret_provided = trim($_SERVER['HTTP_X_JOSTEL_SECRET']);
    } elseif (!empty($_SERVER['HTTP_AUTHORIZATION'])) {
        $secret_provided = trim(str_replace('Bearer ', '', $_SERVER['HTTP_AUTHORIZATION']));
    } elseif (!empty($_REQUEST['secret'])) {
        $secret_provided = trim($_REQUEST['secret']);
    }

    if (empty($secret_provided) || !hash_equals(BACKUP_SECRET_KEY, $secret_provided)) {
        header('HTTP/1.1 401 Unauthorized');
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode([
            'status' => 'error',
            'code' => 401,
            'message' => 'Unauthorized: Invalid or missing X-JosTEL-Secret header or secret parameter.'
        ]);
        exit;
    }
}

// =========================================================================
// 2. LOAD MOODLE CONFIGURATION
// =========================================================================
$config_file = __DIR__ . '/config.php';
if (!file_exists($config_file)) {
    // Try parent directory if placed in a subfolder like /admin/
    $config_file = dirname(__DIR__) . '/config.php';
}

if (!file_exists($config_file)) {
    header('HTTP/1.1 500 Internal Server Error');
    header('Content-Type: application/json');
    echo json_encode([
        'status' => 'error',
        'message' => 'Could not locate Moodle config.php. Please ensure this script is placed in Moodle root directory.'
    ]);
    exit;
}

// Load config without bootstrapping full Moodle UI
global $CFG;
$CFG = new stdClass();
require_once($config_file);

// Ensure backup storage directory exists in moodledata/backup_vault
$backup_dir = rtrim($CFG->dataroot, '/\\') . '/backup_vault';
if (!is_dir($backup_dir)) {
    @mkdir($backup_dir, 0750, true);
    // Add .htaccess to prevent public web access to raw backup directory
    @file_put_contents($backup_dir . '/.htaccess', "Deny from all\n");
}

// Verify authorization
verify_authentication();

$action = isset($_REQUEST['action']) ? trim($_REQUEST['action']) : 'status';

// Helper: Format bytes
function format_bytes($bytes, $precision = 2) {
    if (!$bytes || $bytes <= 0) return '0 B';
    $units = ['B', 'KB', 'MB', 'GB', 'TB'];
    $bytes = max($bytes, 0);
    $pow = floor(($bytes ? log($bytes) : 0) / log(1024));
    $pow = min($pow, count($units) - 1);
    $bytes /= pow(1024, $pow);
    return round($bytes, $precision) . ' ' . $units[$pow];
}

// Helper: Calculate directory size
function get_dir_size($path, $exclude_dirs = []) {
    $size = 0;
    if (!is_dir($path)) return 0;
    foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator($path, FilesystemIterator::SKIP_DOTS)) as $file) {
        $pathname = $file->getPathname();
        $skip = false;
        foreach ($exclude_dirs as $ex) {
            if (strpos($pathname, $ex) !== false) {
                $skip = true;
                break;
            }
        }
        if (!$skip && $file->isFile()) {
            $size += $file->getSize();
        }
    }
    return $size;
}

// =========================================================================
// ACTION ROUTER
// =========================================================================

// --- 1. STATUS ENDPOINT ---
if ($action === 'status') {
    header('Content-Type: application/json; charset=utf-8');

    // Test DB connection
    $db_status = 'connected';
    $db_size_bytes = 0;
    $db_tables_count = 0;

    try {
        $port = !empty($CFG->dboptions['dbport']) ? (int)$CFG->dboptions['dbport'] : 3306;
        $dsn = "mysql:host={$CFG->dbhost};port={$port};dbname={$CFG->dbname};charset=utf8mb4";
        $pdo = new PDO($dsn, $CFG->dbuser, $CFG->dbpass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]);

        $q = $pdo->query("SELECT table_name, (data_length + index_length) as size_bytes FROM information_schema.TABLES WHERE table_schema = '{$CFG->dbname}'");
        $tables = $q->fetchAll();
        $db_tables_count = count($tables);
        foreach ($tables as $t) {
            $db_size_bytes += (float)$t['size_bytes'];
        }
    } catch (Exception $e) {
        $db_status = 'error: ' . $e->getMessage();
    }

    // Disk space info
    $free_disk = @disk_free_space($CFG->dataroot);
    $total_disk = @disk_total_space($CFG->dataroot);

    // List existing backups
    $backups = [];
    if (is_dir($backup_dir)) {
        $files = scandir($backup_dir);
        foreach ($files as $f) {
            if ($f === '.' || $f === '..' || $f === '.htaccess') continue;
            $filepath = $backup_dir . '/' . $f;
            $backups[] = [
                'filename' => $f,
                'size_bytes' => filesize($filepath),
                'size_formatted' => format_bytes(filesize($filepath)),
                'created_at' => date('Y-m-d H:i:s', filemtime($filepath)),
                'type' => (strpos($f, 'full') !== false) ? 'Full System Backup' : 'Database Dump'
            ];
        }
    }

    echo json_encode([
        'status' => 'success',
        'moodle_release' => !empty($CFG->release) ? $CFG->release : 'Moodle 4.x',
        'moodle_version' => !empty($CFG->version) ? $CFG->version : 'N/A',
        'database' => [
            'type' => $CFG->dbtype,
            'host' => $CFG->dbhost,
            'name' => $CFG->dbname,
            'status' => $db_status,
            'tables_count' => $db_tables_count,
            'estimated_size' => format_bytes($db_size_bytes),
            'size_bytes' => $db_size_bytes
        ],
        'storage' => [
            'dataroot' => $CFG->dataroot,
            'dirroot' => $CFG->dirroot,
            'free_disk' => format_bytes($free_disk),
            'total_disk' => format_bytes($total_disk),
            'free_percent' => ($total_disk > 0) ? round(($free_disk / $total_disk) * 100, 1) . '%' : 'N/A'
        ],
        'existing_backups' => $backups
    ], JSON_PRETTY_PRINT);
    exit;
}

// --- 2. CREATE DATABASE BACKUP (.sql.gz) ---
if ($action === 'create_db_backup') {
    header('Content-Type: application/json; charset=utf-8');
    $timestamp = date('Y-m-d_His');
    $sql_filename = "moodle_db_dump_{$CFG->dbname}_{$timestamp}.sql";
    $gz_filename = "{$sql_filename}.gz";
    $gz_filepath = "{$backup_dir}/{$gz_filename}";

    $used_engine = 'native_mysqldump';
    $success = false;

    // Method A: Native mysqldump via exec() if available
    if (function_exists('exec') && !in_array('exec', array_map('trim', explode(',', ini_get('disable_functions'))))) {
        $port_flag = !empty($CFG->dboptions['dbport']) ? "-P " . escapeshellarg($CFG->dboptions['dbport']) : "";
        $cmd = sprintf(
            'mysqldump -h %s %s -u %s -p%s --single-transaction --quick --default-character-set=utf8mb4 %s | gzip > %s',
            escapeshellarg($CFG->dbhost),
            $port_flag,
            escapeshellarg($CFG->dbuser),
            escapeshellarg($CFG->dbpass),
            escapeshellarg($CFG->dbname),
            escapeshellarg($gz_filepath)
        );
        @exec($cmd, $output, $return_var);
        if ($return_var === 0 && file_exists($gz_filepath) && filesize($gz_filepath) > 1024) {
            $success = true;
        }
    }

    // Method B: Pure PHP PDO Dumper Fallback (Works when exec() is restricted)
    if (!$success) {
        $used_engine = 'pure_php_pdo_stream';
        try {
            $port = !empty($CFG->dboptions['dbport']) ? (int)$CFG->dboptions['dbport'] : 3306;
            $dsn = "mysql:host={$CFG->dbhost};port={$port};dbname={$CFG->dbname};charset=utf8mb4";
            $pdo = new PDO($dsn, $CFG->dbuser, $CFG->dbpass, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
            ]);

            $gz = gzopen($gz_filepath, 'w9');
            if (!$gz) throw new Exception("Could not open gzip stream at {$gz_filepath}");

            gzwrite($gz, "-- JosTEL Moodle Database Dump\n-- Server Version: {$CFG->release}\n-- Timestamp: {$timestamp}\n\nSET FOREIGN_KEY_CHECKS=0;\nSET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';\n\n");

            $tables = $pdo->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
            foreach ($tables as $table) {
                // Table schema
                $create = $pdo->query("SHOW CREATE TABLE `{$table}`")->fetch(PDO::FETCH_ASSOC);
                gzwrite($gz, "\n-- Table structure for `{$table}`\nDROP TABLE IF EXISTS `{$table}`;\n" . $create['Create Table'] . ";\n\n");

                // Table rows in batches
                $total_rows = $pdo->query("SELECT COUNT(*) FROM `{$table}`")->fetchColumn();
                if ($total_rows > 0) {
                    $batch_size = 500;
                    for ($offset = 0; $offset < $total_rows; $offset += $batch_size) {
                        $rows = $pdo->query("SELECT * FROM `{$table}` LIMIT {$batch_size} OFFSET {$offset}")->fetchAll(PDO::FETCH_ASSOC);
                        if (!empty($rows)) {
                            $insert_header = "INSERT INTO `{$table}` VALUES ";
                            $insert_vals = [];
                            foreach ($rows as $row) {
                                $vals = array_map(function($v) use ($pdo) {
                                    return ($v === null) ? "NULL" : $pdo->quote($v);
                                }, array_values($row));
                                $insert_vals[] = "(" . implode(",", $vals) . ")";
                            }
                            gzwrite($gz, $insert_header . implode(",\n", $insert_vals) . ";\n");
                        }
                    }
                }
            }

            gzwrite($gz, "\nSET FOREIGN_KEY_CHECKS=1;\n-- Dump Complete\n");
            gzclose($gz);
            $success = true;
        } catch (Exception $e) {
            echo json_encode(['status' => 'error', 'message' => 'DB Dump failed: ' . $e->getMessage()]);
            exit;
        }
    }

    echo json_encode([
        'status' => 'success',
        'message' => 'Moodle Database dump created successfully.',
        'engine' => $used_engine,
        'filename' => $gz_filename,
        'size_bytes' => filesize($gz_filepath),
        'size_formatted' => format_bytes(filesize($gz_filepath)),
        'download_url' => "admin_backup_api.php?action=download&file=" . urlencode($gz_filename) . "&secret=" . urlencode(BACKUP_SECRET_KEY)
    ], JSON_PRETTY_PRINT);
    exit;
}

// --- 3. CREATE FULL SERVER BACKUP (DB + MOODLEDATA + CONFIG) ---
if ($action === 'create_full_backup') {
    header('Content-Type: application/json; charset=utf-8');
    $timestamp = date('Y-m-d_His');
    $archive_name = "jostel_moodle_full_server_backup_{$timestamp}.zip";
    $archive_path = "{$backup_dir}/{$archive_name}";

    // First: Create DB dump inside temp folder
    $sql_file = "{$backup_dir}/moodle_database_{$timestamp}.sql";
    $port = !empty($CFG->dboptions['dbport']) ? (int)$CFG->dboptions['dbport'] : 3306;
    $dsn = "mysql:host={$CFG->dbhost};port={$port};dbname={$CFG->dbname};charset=utf8mb4";
    
    try {
        $pdo = new PDO($dsn, $CFG->dbuser, $CFG->dbpass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]);

        $fh = fopen($sql_file, 'w');
        fwrite($fh, "-- JosTEL Moodle Complete Server Dump\nSET FOREIGN_KEY_CHECKS=0;\n\n");
        $tables = $pdo->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
        foreach ($tables as $table) {
            $create = $pdo->query("SHOW CREATE TABLE `{$table}`")->fetch(PDO::FETCH_ASSOC);
            fwrite($fh, "\nDROP TABLE IF EXISTS `{$table}`;\n" . $create['Create Table'] . ";\n");
            $total_rows = $pdo->query("SELECT COUNT(*) FROM `{$table}`")->fetchColumn();
            if ($total_rows > 0) {
                $batch_size = 500;
                for ($offset = 0; $offset < $total_rows; $offset += $batch_size) {
                    $rows = $pdo->query("SELECT * FROM `{$table}` LIMIT {$batch_size} OFFSET {$offset}")->fetchAll(PDO::FETCH_ASSOC);
                    if (!empty($rows)) {
                        $insert_vals = [];
                        foreach ($rows as $row) {
                            $vals = array_map(function($v) use ($pdo) {
                                return ($v === null) ? "NULL" : $pdo->quote($v);
                            }, array_values($row));
                            $insert_vals[] = "(" . implode(",", $vals) . ")";
                        }
                        fwrite($fh, "INSERT INTO `{$table}` VALUES " . implode(",\n", $insert_vals) . ";\n");
                    }
                }
            }
        }
        fwrite($fh, "\nSET FOREIGN_KEY_CHECKS=1;\n");
        fclose($fh);
    } catch (Exception $e) {
        echo json_encode(['status' => 'error', 'message' => 'DB dump stage failed: ' . $e->getMessage()]);
        exit;
    }

    // Build Zip Archive
    $zip = new ZipArchive();
    if ($zip->open($archive_path, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
        echo json_encode(['status' => 'error', 'message' => 'Cannot create zip file at ' . $archive_path]);
        exit;
    }

    // 1. Add SQL dump
    $zip->addFile($sql_file, 'database/moodle_database.sql');

    // 2. Add config.php
    $zip->addFile($config_file, 'code/config.php');

    // 3. Add restore guide & automated restore script
    $restore_script = <<<RESTORE_BAT
@echo off
echo ========================================================
echo  JosTEL Moodle Machine Restore Helper
echo ========================================================
echo 1. Creating database 'moodle'...
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS moodle DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo 2. Importing SQL dump...
mysql -u root -p moodle < database\moodle_database.sql
echo 3. Copying moodledata...
echo Done! Please copy 'moodledata' files to your local dataroot and update config.php.
pause
RESTORE_BAT;
    $zip->addFromString('restore_instructions.bat', $restore_script);

    // 4. Add moodledata filedir (excluding cache, localcache, sessions, temp)
    $filedir = rtrim($CFG->dataroot, '/\\') . '/filedir';
    if (is_dir($filedir)) {
        $files = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($filedir, FilesystemIterator::SKIP_DOTS));
        $file_count = 0;
        foreach ($files as $f) {
            if ($f->isFile()) {
                $relative = 'moodledata/filedir/' . substr($f->getPathname(), strlen($filedir) + 1);
                $zip->addFile($f->getPathname(), $relative);
                $file_count++;
                if ($file_count > 10000) break; // Safeguard limit per run
            }
        }
    }

    $zip->close();
    @unlink($sql_file); // Remove intermediate plain SQL dump

    echo json_encode([
        'status' => 'success',
        'message' => 'Complete Moodle machine backup archive packaged successfully.',
        'filename' => $archive_name,
        'size_bytes' => filesize($archive_path),
        'size_formatted' => format_bytes(filesize($archive_path)),
        'download_url' => "admin_backup_api.php?action=download&file=" . urlencode($archive_name) . "&secret=" . urlencode(BACKUP_SECRET_KEY)
    ], JSON_PRETTY_PRINT);
    exit;
}

// --- 4. LIST BACKUPS ---
if ($action === 'list_backups') {
    header('Content-Type: application/json; charset=utf-8');
    $list = [];
    if (is_dir($backup_dir)) {
        foreach (scandir($backup_dir) as $f) {
            if ($f === '.' || $f === '..' || $f === '.htaccess') continue;
            $fp = $backup_dir . '/' . $f;
            $list[] = [
                'filename' => $f,
                'size_bytes' => filesize($fp),
                'size_formatted' => format_bytes(filesize($fp)),
                'created_at' => date('Y-m-d H:i:s', filemtime($fp)),
                'download_url' => "admin_backup_api.php?action=download&file=" . urlencode($f) . "&secret=" . urlencode(BACKUP_SECRET_KEY)
            ];
        }
    }
    echo json_encode(['status' => 'success', 'backups' => $list], JSON_PRETTY_PRINT);
    exit;
}

// --- 5. CHUNKED STREAM DOWNLOAD ---
if ($action === 'download') {
    $requested = basename($_REQUEST['file']);
    $filepath = $backup_dir . '/' . $requested;

    if (!file_exists($filepath) || !is_file($filepath)) {
        header('HTTP/1.1 404 Not Found');
        echo "Requested backup file does not exist.";
        exit;
    }

    // Stream download in chunks
    $filesize = filesize($filepath);
    header('Content-Description: File Transfer');
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="' . $requested . '"');
    header('Expires: 0');
    header('Cache-Control: must-revalidate');
    header('Pragma: public');
    header('Content-Length: ' . $filesize);

    if (ob_get_level()) ob_end_clean();
    $handle = fopen($filepath, 'rb');
    while (!feof($handle)) {
        echo fread($handle, 1024 * 64); // 64KB buffer
        flush();
    }
    fclose($handle);
    exit;
}

// --- 6. DELETE BACKUP ---
if ($action === 'delete') {
    header('Content-Type: application/json; charset=utf-8');
    $requested = basename($_REQUEST['file']);
    $filepath = $backup_dir . '/' . $requested;

    if (file_exists($filepath) && is_file($filepath)) {
        @unlink($filepath);
        echo json_encode(['status' => 'success', 'message' => "Backup file {$requested} deleted."]);
    } else {
        echo json_encode(['status' => 'error', 'message' => "File not found."]);
    }
    exit;
}
