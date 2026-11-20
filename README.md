# VideoHub

VideoHub is a Django video library with phone/login-name authentication, saved videos, likes, reactions, and a staff dashboard.

## Local setup

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. On first visit the welcome screen leads to login after three seconds. Register an account or create a superuser with `python manage.py createsuperuser`.

## Render deployment

The included `render.yaml` provisions a Python web service with a persistent disk. SQLite and uploaded media are stored on that disk. The service runs migrations and then `ensure_videohub_admin` on startup, so the administrator is provisioned after the hosted database is ready.

After creating the Render Blueprint, set the secret environment variable `VH_ADMIN_PASSWORD` in the web service settings. The configured admin phone, login, and display name are `930804866`, `ybek`, and `Yahyobek Yaqubboyev`. The password is intentionally not stored in this repository; choose the desired value in Render's environment settings.

The persistent disk requires a paid Render web-service plan. Local `db.sqlite3`, media uploads, virtual environments, and collected static output are excluded from Git.