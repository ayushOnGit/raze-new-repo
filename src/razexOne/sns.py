import boto3
from .settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_REGION_NAME


class SNSService:
    def __init__(self):
        self.client = boto3.client(
            "sns",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_S3_REGION_NAME,
        )

    def send_otp(self, phone_number, otp, expiry_in_mins=5):
        """
        Send OTP via SMS using AWS SNS
        """
        try:
            response = self.client.publish(
                PhoneNumber=phone_number,
                Message=f"Your OTP is {otp}. It is valid for {expiry_in_mins} minutes. Team RazexOne",
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {
                        "DataType": "String",
                        "StringValue": "RazexOne",
                    },
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",
                    },
                },
            )
            return response["MessageId"]
        except Exception as e:
            raise Exception(f"Failed to send OTP: {str(e)}")

    @classmethod
    def get_instance(cls):
        """
        Singleton pattern to get the SNSService instance.
        """
        if not hasattr(cls, "instance"):
            cls.instance = cls()
        return cls.instance
