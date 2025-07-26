import botocore
import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig


class AWSSecretsManager:
    def __init__(self, region_name, access_key=None, secret_key=None):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            "secretsmanager",
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.cache_config = SecretCacheConfig()
        self.cache = SecretCache(config=self.cache_config, client=self.client)

    def get_secret(self, secret_name):
        try:
            secret = self.cache.get_secret_string(secret_name)
            return secret
        except botocore.exceptions.ClientError as e:
            # Handle the exception as needed
            print(f"Error retrieving secret from AWS: {secret_name}, error: {e}")
            return None


class SecretManager:
    def __init__(self, aws_secrets_manager=None, env=None):
        self.env = env
        self.aws_secrets_manager = aws_secrets_manager

    def get_secret(self, secret_name, default=None):
        if self.aws_secrets_manager is not None:
            # Fetch secret from AWS Secrets Manager
            secret = self.aws_secrets_manager.get_secret(secret_name)
            if secret is None:
                return default
        else:
            # Fetch secret from environment variables
            return self.env(secret_name, default=default)
