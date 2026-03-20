# -*- coding: utf-8 -*-
"""
Конфиг gunicorn: порт только из os.environ['PORT'] — без shell и $PORT в кавычках
(на Render одинарные кавычки вокруг команды ломают подстановку $PORT).
"""
import os

# На Render не подставлять 10000 по умолчанию — иначе слушаем не тот порт, что ждёт платформа
if os.environ.get("RENDER") and not os.environ.get("PORT"):
    raise RuntimeError("PORT must be set when RENDER=1")
_port = os.environ.get("PORT", "5001")
bind = "0.0.0.0:" + str(_port).strip()

workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
worker_class = "sync"
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
# Ошибки импорта app — до fork воркеров (проще отладить в логах)
preload_app = False
# Печать в лог при старте (Render)
print(f"[gunicorn.conf] bind={bind} PORT env={_port!r}", flush=True)
