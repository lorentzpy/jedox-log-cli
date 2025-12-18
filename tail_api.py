#!/usr/bin/env python3
import requests
import time
import argparse
import signal
import sys
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

# ---------------- CLI ----------------

parser = argparse.ArgumentParser(
    description="CLI for the Jedox Logs API"
)

services = ["In-Memory","Spreadsheet","Apache","Integrator","RPC","PSF","Supervision","Scheduler","AI","OData","Views Backend","Access Logs"]

parser.add_argument("--cloud_instance", required=True, help="logs API URL")
parser.add_argument("--token", help="Bearer token")
parser.add_argument("--interval", type=float, default=2.0, help="Interval in seconds")
parser.add_argument("--max-lines", type=int, default=20, help="Number of log lines to display. not used yet")
#parser.add_argument("--level", choices=["info", "warning", "error", "debug", "warning_only", "error_only", "debug_only"], help="Filter by level")
parser.add_argument("--level", help="Filter by level")
parser.add_argument("--service", choices=services, help="Filter by service")
parser.add_argument("--from_date", help="From, ISO8601 format")
parser.add_argument("--to_date", help="To, ISO8601 format")
parser.add_argument("--sort", choices=["asc", "desc"], help="Sort by")

args = parser.parse_args()

# ---------------- Config ----------------
headers = {}

if args.token:
    headers["Authorization"] = f"Bearer {args.token}"

seen = set()
buffer = []

# info by default
level = "info"

# sort desc by default
sort = "desc"
if args.sort:
    sort = args.sort

from_date_str = args.from_date
to_date_str = args.to_date

from_date = None
to_date = None

# parse from_date if set
if from_date_str:
    try:
        from_date = datetime.fromisoformat(from_date_str)
    except ValueError:
        print("[bold red]Error:[/bold red] from_date must be in ISO8601 format (YYYY-MM-DD)")
        exit(1)

# parse to_date if set
if to_date_str:
    try:
        to_date = datetime.fromisoformat(to_date_str)
    except ValueError:
        print("Error: to_date must be in ISO8601 format (YYYY-MM-DD)")
        exit(1)

# sanitize from and to spans
if from_date and to_date and from_date >= to_date:
    print(f"Error: from_date ({from_date_str}) must be anterior to to_date ({to_date_str})")
    exit(1)

# warning displays warning and info, error displays error, warning and info, etc.
if args.level:
    if args.level == "warning":
        level = "info,warning"
    elif args.level == "error":
        level = "info,warning,error"
    elif args.level == "debug":
        level = "info,warning,error,debug"
    elif args.level.endswith("_only"):
        level = args.level.replace("_only", "")
    
# ----------------- Ctrl+C managment  -----------------
def handle_exit(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


# ---------------- Logic ----------------

def fetch_logs():
    try:
        url_query_params = dict()
        
        if args.service:
            url_query_params["service"] = args.service
            
        url_query_params["level"] = level
        
        # sort desc by default (newest first)
        url_query_params["sort"] = sort

        if from_date:
            url_query_params["from"] = args.from_date

        if to_date:
            url_query_params["to"] = args.to_date
        
        url = f"https://logs.{args.cloud_instance}.cloud.jedox.com/logs"
        
        r = requests.get(url, headers=headers, timeout=10, params=url_query_params)
               
        r.raise_for_status()
        data = r.json()

        if isinstance(data, dict) and "logs" in data:
            # reversed to get the newest logs at the end
            return reversed(data["logs"])

        print(Fore.RED + "[ERROR] JSON Format unexpected")
        return []

    except Exception as e:
        print(Fore.RED + f"[ERROR] {e}")
        return []
        
def colorize(level, text):
    if level == "error":
        return Fore.RED + text
    if level == "warning":
        return Fore.YELLOW + text
    return text

def main():
    while True:
        logs = fetch_logs()

        for log in logs:
            ts = log.get("date", "")
            level = log.get("level")
            msg = log.get("message", str(log))

            log_id = f"{ts}|{level}|{msg}"
            if log_id in seen:
                continue

            seen.add(log_id)

            line = f"{ts}\t{level:<5}\t{msg}"
            colored = colorize(level, line)

            buffer.append(colored)
            buffer[:] = buffer[-args.max_lines:]

            print(colored)

        time.sleep(args.interval)

# ---------------- Entry ----------------
if __name__ == "__main__":
    main()
