# Razex API server

Current stack: Django/Postgres/Redis

## Developer setup

You don't need to run Postgres or Redis server currently since we are not using them, will be falling back to Sqlite for now.
The process is similar to [dev setup](https://docs.pretix.eu/en/latest/development/setup.html) and can be used as a reference.

0. Install latest python, git.

1. After git clone cd to your repo and run:
```
python3 -m venv env
```

2. Activate the virtual env by:
```
source env/bin/activate # on mac or linux
env/Scripts/Activate.ps1 # on windows
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Configure dev settings:
    - Rename `sample.env` to `.env` and update the file variables as needed.
    - If you want to enable Firebase authentication, go to [firebase console](https://console.firebase.google.com/) and generate a SERVICE ACCOUNT KEY file for your project, make sure you have enabled Auth options as needed. Save it somewhere on your machine and mention the file path in `FIREBASE_SERVICE_ACCOUNT_KEY_PATH` variable.

5. Apply any database migration
```
cd src # Go to src directory
python manage.py migrate --run-syncdb
```

6. Run server in dev mode
```
python manage.py runserver
```

7. Visit the swagger endpoint for docs: http://127.0.0.1:8000/swagger/
