#!/usr/bin/env python3
"""
Локальный запуск: python run.py
На Render используйте: gunicorn -c gunicorn.conf.py app:app
"""
import os
import sys

def main():
    root = os.path.abspath(os.path.dirname(__file__))
    cfg = os.path.join(root, "gunicorn.conf.py")
    print(f"[run.py] gunicorn -c {cfg} app:app", file=sys.stderr, flush=True)
    sys.argv = ["gunicorn", "-c", cfg, "app:app"]
    os.chdir(root)
    from gunicorn.app.wsgiapp import run
    run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[run.py] FATAL: {e!r}", file=sys.stderr, flush=True)
        raise
