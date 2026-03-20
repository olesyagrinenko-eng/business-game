# Деплой на Render (порт / health check)

## Если в логах всё ещё **gunicorn**

Сервис **не** подхватил `render.yaml` или в **Dashboard** задана своя команда.

1. Откройте **Render Dashboard** → ваш **Web Service** → **Settings**.
2. Найдите **Start Command** и задайте **ровно**:

   ```bash
   python serve_waitress.py
   ```

3. **Save Changes** → **Manual Deploy** → при необходимости **Clear build cache**.

4. После деплоя в **Logs** в начале должна быть строка:

   ```text
   === serve_waitress.py (Waitress) — если вместо этого gunicorn...
   ```

   Если снова идут строки `Starting gunicorn` — команда запуска **не** обновилась.

## Почему Waitress

На Render проверка «открыт HTTP-порт» иногда **не проходит** с **gunicorn** (мастер/воркер, строка `Control socket` в логах). **Waitress** — один процесс, сразу отвечает по HTTP на `PORT`.

## Health check

В настройках сервиса: **Health Check Path** = `/health`.

При необходимости увеличьте **Health Check Grace Period** / таймаут в настройках Render.

## Root Directory

Если репозиторий большой, укажите **Root Directory** = каталог с `app.py` (например `бизнес игра/game-web` или только `game-web`, если вынесли в корень).
