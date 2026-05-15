from app.config import settings


class EtsyAuth:
    def __init__(self):
        self.api_key = settings.etsy_api_key
        self.api_secret = settings.etsy_api_secret

    def get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.api_secret}",
            "Content-Type": "application/json",
        }


etsy_auth = EtsyAuth()
