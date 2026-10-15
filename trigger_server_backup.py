#!/usr/bin/env python3
"""
JosTEL Moodle Secure Server Backup Trigger & Downloader CLI
St. Joseph's College (Autonomous), Tiruchirappalli

Automates triggering and downloading:
  1. Full Database Dump (.sql.gz)
  2. Complete Machine Migration Archive (.zip)
directly from the Moodle server using admin_backup_api.php.

Zero External Dependencies: Uses standard library only (urllib, json, ssl).
"""

import os
import sys
import argparse
import json
import time
import ssl
import urllib.request
import urllib.parse
import urllib.error

# Ensure proper UTF-8 stdout on Windows CMD / PowerShell
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_SERVER_URL = "https://service.sjctni.edu/jostel/moodle/admin_backup_api.php"
DEFAULT_SECRET = "JosTEL_Moodle_Secure_Vault_2026_Key"
BACKUP_LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_backups")


def get_ssl_context():
    ctx = ssl.create_default_context()
    # Bypass strict cert validation if local college proxy or custom CA is present
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def format_bytes(num_bytes):
    if not num_bytes or num_bytes <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def send_api_request(url, params=None, data=None, secret=DEFAULT_SECRET, timeout=600):
    headers = {
        "X-JosTEL-Secret": secret,
        "User-Agent": "JosTEL-Backup-CLI/1.0"
    }

    if params:
        query_string = urllib.parse.urlencode(params)
        sep = '&' if '?' in url else '?'
        target_url = f"{url}{sep}{query_string}"
    else:
        target_url = url

    encoded_data = None
    if data:
        encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(target_url, data=encoded_data, headers=headers)
    ctx = get_ssl_context()
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            body = response.read().decode('utf-8')
            return json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("[!] ERROR: 401 Unauthorized - The Vault Secret Key is invalid.")
        else:
            print(f"[!] HTTP Error {e.code}: {e.read().decode('utf-8', errors='replace')[:250]}")
        return None
    except Exception as ex:
        print(f"[!] Request Exception: {ex}")
        return None


def stream_download(download_url, dest_filepath, secret=DEFAULT_SECRET, expected_size=0):
    os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
    print(f"\n[+] Starting Stream Download: {os.path.basename(dest_filepath)}")
    start_time = time.time()
    
    headers = {
        "X-JosTEL-Secret": secret,
        "User-Agent": "JosTEL-Backup-CLI/1.0"
    }
    req = urllib.request.Request(download_url, headers=headers)
    ctx = get_ssl_context()

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=1800) as response:
            content_length = response.headers.get('Content-Length')
            total_size = int(content_length) if content_length else expected_size
            downloaded = 0

            with open(dest_filepath, 'wb') as f:
                while True:
                    chunk = response.read(64 * 1024) # 64KB buffer
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        sys.stdout.write(f"\r--> Stream: [{pct:5.1f}%] {mb_done:6.1f} MB / {mb_total:6.1f} MB")
                    else:
                        mb_done = downloaded / (1024 * 1024)
                        sys.stdout.write(f"\r--> Streamed: {mb_done:6.1f} MB")
                    sys.stdout.flush()

        elapsed = time.time() - start_time
        actual_size = os.path.getsize(dest_filepath)
        print(f"\n[OK] Download Complete in {elapsed:.1f}s: {dest_filepath} ({format_bytes(actual_size)})\n")
        return True
    except Exception as e:
        print(f"\n[!] Download error: {e}")
        return False


def check_status(api_url, secret):
    print(f"\n[+] Connecting to Server Backup Vault: {api_url}")
    data = send_api_request(api_url, params={"action": "status", "secret": secret}, secret=secret, timeout=30)
    if not data or data.get("status") != "success":
        return False

    print("\n========================================================")
    print("          JOSTEL MOODLE SERVER SYSTEM DIAGNOSTICS        ")
    print("========================================================")
    print(f"Moodle Release  : {data.get('moodle_release')} (v{data.get('moodle_version')})")
    
    db = data.get("database", {})
    print(f"Database Type   : {db.get('type')} on {db.get('host')}")
    print(f"Database Name   : {db.get('name')}")
    print(f"Database Status : {db.get('status')}")
    print(f"Total DB Tables : {db.get('tables_count')}")
    print(f"Est. DB Size    : {db.get('estimated_size')}")

    storage = data.get("storage", {})
    print(f"Dataroot Path   : {storage.get('dataroot')}")
    print(f"Disk Free Space : {storage.get('free_disk')} / {storage.get('total_disk')} ({storage.get('free_percent')} free)")

    backups = data.get("existing_backups", [])
    print(f"\nExisting Vault Backups on Server: {len(backups)}")
    if backups:
        print("-" * 75)
        print(f"{'Filename':<42} | {'Type':<18} | {'Size':<10}")
        print("-" * 75)
        for b in backups:
            print(f"{b.get('filename'):<42} | {b.get('type'):<18} | {b.get('size_formatted'):<10}")
        print("-" * 75)
    print("========================================================\n")
    return True


def trigger_db_backup(api_url, secret, download_now=True):
    print(f"\n[+] Triggering Server-Side Moodle Database Dump...")
    print("    (This may take 10-60 seconds depending on DB size...)")
    data = send_api_request(
        api_url,
        data={"action": "create_db_backup", "secret": secret},
        secret=secret,
        timeout=600
    )
    if not data or data.get("status") != "success":
        print("[!] DB Dump Failed.")
        return False

    print(f"[OK] Database Dump Generated Successfully!")
    print(f"     Filename : {data.get('filename')}")
    print(f"     Size     : {data.get('size_formatted')}")
    print(f"     Engine   : {data.get('engine')}")

    if download_now:
        download_url = data.get("download_url")
        if not download_url.startswith("http"):
            base_endpoint = api_url.rsplit('/', 1)[0]
            download_url = f"{base_endpoint}/{download_url}"
        dest = os.path.join(BACKUP_LOCAL_DIR, data.get("filename"))
        stream_download(download_url, dest, secret=secret, expected_size=data.get("size_bytes", 0))

    return True


def trigger_full_backup(api_url, secret, download_now=True):
    print(f"\n[+] Triggering Complete Moodle Bare-Metal Machine Archive...")
    print("    (Dumping DB, config.php, moodledata files & packaging .zip...)")
    print("    (This can take 1-3 minutes. Please wait...)")
    data = send_api_request(
        api_url,
        data={"action": "create_full_backup", "secret": secret},
        secret=secret,
        timeout=1800
    )
    if not data or data.get("status") != "success":
        print("[!] Full Backup Failed.")
        return False

    print(f"[OK] Full Server Machine Backup Archive Generated!")
    print(f"     Filename : {data.get('filename')}")
    print(f"     Size     : {data.get('size_formatted')}")

    if download_now:
        download_url = data.get("download_url")
        if not download_url.startswith("http"):
            base_endpoint = api_url.rsplit('/', 1)[0]
            download_url = f"{base_endpoint}/{download_url}"
        dest = os.path.join(BACKUP_LOCAL_DIR, data.get("filename"))
        stream_download(download_url, dest, secret=secret, expected_size=data.get("size_bytes", 0))

    return True


def list_and_download(api_url, secret, specific_file=None):
    if specific_file:
        download_url = f"{api_url}?action=download&file={urllib.parse.quote(specific_file)}&secret={urllib.parse.quote(secret)}"
        dest = os.path.join(BACKUP_LOCAL_DIR, specific_file)
        stream_download(download_url, dest, secret=secret)
        return

    data = send_api_request(api_url, params={"action": "list_backups", "secret": secret}, secret=secret, timeout=30)
    if not data:
        return
    backups = data.get("backups", [])
    if not backups:
        print("[i] No backups found on server.")
        return

    print("\nAvailable Server Backups:")
    for idx, b in enumerate(backups):
        print(f" [{idx + 1}] {b['filename']} ({b['size_formatted']}) - {b['created_at']}")

    choice = input("\nEnter number to download (or press Enter to cancel): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(backups):
        sel = backups[int(choice) - 1]
        download_url = f"{api_url}?action=download&file={urllib.parse.quote(sel['filename'])}&secret={urllib.parse.quote(secret)}"
        dest = os.path.join(BACKUP_LOCAL_DIR, sel['filename'])
        stream_download(download_url, dest, secret=secret, expected_size=sel.get('size_bytes', 0))


def main():
    parser = argparse.ArgumentParser(description="JosTEL Moodle Secure Server Backup CLI (Zero Dependencies)")
    parser.add_argument("--url", default=DEFAULT_SERVER_URL, help="URL to admin_backup_api.php")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="Vault Secret Key")
    parser.add_argument("--status", action="store_true", help="Check server status and DB health")
    parser.add_argument("--db", action="store_true", help="Create and download full database dump (.sql.gz)")
    parser.add_argument("--full", action="store_true", help="Create and download full machine archive (.zip)")
    parser.add_argument("--list", action="store_true", help="List and interactively download existing backups")
    parser.add_argument("--download", type=str, help="Download a specific backup filename")
    parser.add_argument("--no-download", action="store_true", help="Trigger backup on server without downloading immediately")

    args = parser.parse_args()

    if args.status:
        check_status(args.url, args.secret)
    elif args.db:
        trigger_db_backup(args.url, args.secret, download_now=not args.no_download)
    elif args.full:
        trigger_full_backup(args.url, args.secret, download_now=not args.no_download)
    elif args.download:
        list_and_download(args.url, args.secret, specific_file=args.download)
    elif args.list:
        list_and_download(args.url, args.secret)
    else:
        # Default interactive menu
        print("\n========================================================")
        print("    JosTEL Moodle Secure Server Backup CLI Engine       ")
        print("========================================================")
        print("1. Check Server Diagnostics & Health Status")
        print("2. Dump Full Database (.sql.gz) & Download to Local Machine")
        print("3. Generate Complete Machine Archive (.zip) & Download")
        print("4. List Existing Server Backups & Download")
        print("5. Exit")
        try:
            choice = input("\nSelect an option (1-5): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return
        
        if choice == "1":
            check_status(args.url, args.secret)
        elif choice == "2":
            trigger_db_backup(args.url, args.secret, download_now=True)
        elif choice == "3":
            trigger_full_backup(args.url, args.secret, download_now=True)
        elif choice == "4":
            list_and_download(args.url, args.secret)
        else:
            print("Exiting.")


if __name__ == "__main__":
    main()
