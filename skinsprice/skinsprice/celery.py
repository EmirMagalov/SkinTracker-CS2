from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skinsprice.settings')

app = Celery('skinsprice')

# Загружает настройки Django CELERY_ из settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находит задачи во всех приложениях Django
app.autodiscover_tasks()
