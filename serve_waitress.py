#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск для Render: Waitress (WSGI), один процесс, порт только из os.environ['PORT'].
Часто проходит health-check, чем gunicorn + fork воркеров.
"""
import os
import sys


def main():
    is_render = os.environ.get("RENDER", "").lower() in ("1", "true", "yes")
    raw = os.environ.get("PORT")
    if is_render and not raw:
        print("ERROR: PORT must be set on Render (check Web Service settings)", file=sys.stderr, flush=True)
        sys.exit(1)
    port = int(raw) if raw else int(os.environ.get("PORT", "5001"))

    print(f"[waitress] bind=0.0.0.0:{port} RENDER={is_render} PORT_env={raw!r}", flush=True)

    from waitress import serve
    from app import app

    serve(
        app,
        host="0.0.0.0",
        port=port,
        threads=4,
        channel_timeout=120,
        cleanup_interval=30,
    )


if __name__ == "__main__":
    main()
