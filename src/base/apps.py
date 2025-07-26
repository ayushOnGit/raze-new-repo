from django.apps import AppConfig
import firebase_admin
import json
from firebase_admin import credentials
from razexOne.settings import (
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH,
    FIREBASE_SERVICE_ACCOUNT_KEY_JSON,
)


class BaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "base"

    def ready(self):
        # Initialize the Firebase app
        cert = FIREBASE_SERVICE_ACCOUNT_KEY_PATH
        if FIREBASE_SERVICE_ACCOUNT_KEY_JSON:
            try:
                cert = json.loads(FIREBASE_SERVICE_ACCOUNT_KEY_JSON)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                return
        if not cert:
            print("WARNING: Firebase service account key path not set.")
        else:
            cred = credentials.Certificate(cert)
            firebase_admin.initialize_app(cred)
