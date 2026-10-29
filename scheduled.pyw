"""Windows scheduled-task entry point: runs fetch.py with no window and appends to fetch.log.

YouTube blocks downloads from GitHub's runners, so the mirror runs from an office PC instead.
Registered with:  schtasks /create /tn "Biran kiosk videos" /sc hourly /mo 3 /tr "pythonw <this file>"
"""
import datetime
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["PYTHONUTF8"] = "1"
sys.path.insert(0, HERE)

log = open(os.path.join(HERE, "fetch.log"), "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = log
print(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M}")
try:
    import fetch
    fetch.main()
except SystemExit as e:
    print("exit:", e)
except Exception:
    traceback.print_exc()
