source ../venv_rtops/bin/activate
nohup celery -A celery_app.main worker -l info >celery.log 2>&1 &
nohup celery -A celery_app.main beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler >beat.log 2>&1 &
deactivate
