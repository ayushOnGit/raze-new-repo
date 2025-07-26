import jwt as pyjwt
from razexOne.settings import SECRET_KEY

def encode_jwt(payload: dict) -> str:
    return pyjwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_jwt(token: str) -> dict:
    return pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
