import re
from django.core.exceptions import ValidationError


def validate_phone_number(phone_number):
    """
    Validate if the given phone number is in E.164 format.
    It must start with '+' followed by a country code and digits.

    Example: +911234567890 (Valid), 1234567890 (Invalid), +ABC12345 (Invalid)
    """
    pattern = r"^\+\d{1,4}\d{6,14}$"  # E.164 format: +<1-4 digit country code><6-14 digit number>

    if not re.match(pattern, phone_number):
        raise ValidationError(
            "Invalid phone number format. Must be in E.164 format (e.g., +911234567890)."
        )


def extract_country_code(phone_number):
    """
    Extracts the country code from a valid E.164 phone number.

    Example:
        Input: +911234567890
        Output: +91
    """
    if not phone_number.startswith("+"):
        raise ValueError("Phone number must start with '+' followed by country code.")

    match = re.match(r"^\+(\d{1,4})", phone_number)
    if match:
        return f"+{match.group(1)}"

    raise ValueError("Invalid phone number format. Cannot extract country code.")
