import random

def generate_coupon_code():
    """
    Generate a random coupon code.
    """
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
