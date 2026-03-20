#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск для Render: Waitress (WSGI), один процесс, порт только из os.environ['PORT'].

Если в логах видите gunicorn — в панели Render задана старая Start Command. Задайте:
  python serve_waitress.py
"""
import os
import sys

# Сразу в лог: по этой строке видно, что запущен Waitress, а не gunicorn
print("=== serve_waitress.py (Waitress) — если вместо этого gunicorn, смените Start Command в Render ===", flush=True)


def main():
    is_render = os.environ.get("RENDER", "").lower() in ("1", "true", "yes")
    raw = os.environ.get("PORT")
    if is_render and not raw:
        print("ERROR: PORT must be set on Render (check Web Service settings)", file=sys.stderr, flush=True)
        sys.exit(1)
    port = int(raw) if raw else 5001

    print(f"[waitress] listening http://0.0.0.0:{port}/ RENDER={is_render} PORT_env={raw!r}", flush=True)

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
