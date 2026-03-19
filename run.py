#!/usr/bin/env python3
"""
Запуск gunicorn с портом из переменной PORT (для Render).
Так порт гарантированно подставляется даже если shell не раскрывает $PORT.
"""
import os
import sys

def main():
    port = os.environ.get("PORT", "10000")
    try:
        port = str(int(port))
    except ValueError:
        port = "10000"
    bind = f"0.0.0.0:{port}"
    print(f"[run.py] gunicorn bind={bind} (PORT from env)", file=sys.stderr, flush=True)
    # Запуск gunicorn программно с нужным bind
    sys.argv = [
        "gunicorn",
        "-b", bind,
        "--workers", "1",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "app:app",
    ]
    from gunicorn.app.wsgiapp import run
    run()

if __name__ == "__main__":
    main()
