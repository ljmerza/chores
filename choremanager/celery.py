import os

try:
    from celery import Celery
except ImportError:
    Celery = None

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "choremanager.settings")

if Celery:
    app = Celery("choremanager")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()

    @app.task(bind=True)
    def debug_task(self):
        print(f"Request: {self.request!r}")
