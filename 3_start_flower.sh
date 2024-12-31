source ../venv_rtops/bin/activate
nohup celery -A celery_app.main flower --address=0.0.0.0 --port=5556 >flower.log 2>&1 &
deactivate

