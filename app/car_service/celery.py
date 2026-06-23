import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "car_service.settings")

app = Celery("car_service")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "auto-purchase-every-10-minutes": {
        "task": "purchases.tasks.run_auto_purchase",
        "schedule": crontab(minute="*/10"),  # every 10 minutes
    },
    "refresh-priority-suppliers-every-hour": {
        "task": "purchases.tasks.refresh_priority_suppliers",
        "schedule": crontab(minute=0),  # every hour at :00
    },
}
