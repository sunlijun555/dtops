source ../venv_rtops/bin/activate
nohup python3 manage.py runserver 0.0.0.0:8000 > http.log 2>&1 &
deactivate
