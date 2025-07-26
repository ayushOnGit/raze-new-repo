from django.core.management.base import BaseCommand
from base.models import User
from base.auth import AuthManager
import uuid

class Command(BaseCommand):
    help = "Create an user or generate JWT for an existing user"

    def add_arguments(self, parser):
        parser.add_argument("--create-user", action="store_true", help="Create a new user")
        parser.add_argument("--api-key", type=str, help="Generate JWT for a user by user_id")
    
    def _print_api_key(self, user):
        auth_manager = AuthManager.get_instance()
        auth_backend = auth_manager.get_auth_backend_for_user(user)
        token = auth_backend.generate_jwt_token(user.uid)
        self.stdout.write(self.style.SUCCESS(f"JWT Token: {token}"))

    def handle(self, *args, **options):
        if options["create_user"]:
            uid = input("Enter UID: (Auto-generated if left blank) ")
            if not uid:
                uid = str(uuid.uuid4())
            name = input("Enter Name: ")
            if not name:
                print("Setting name as: " + uid)
                name = uid
            is_staff = input("Is staff? (y/n): ")
            is_staff = is_staff.lower() == "y"

            user = User.objects.create_user(uid=uid, auth_backend="native", is_staff=is_staff, name=name)
            self.stdout.write(self.style.SUCCESS(f"User {user.user_id} created successfully."))
            self._print_api_key(user)
        elif options["api_key"]:
            user_id = options["api_key"]
            try:
                user = User.objects.get(user_id=user_id)
                self._print_api_key(user)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR("User not found."))
        else:
            self.stderr.write(self.style.ERROR("Invalid arguments."))
