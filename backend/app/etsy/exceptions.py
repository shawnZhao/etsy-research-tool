class EtsyAPIError(Exception):
    """Base exception for Etsy API errors."""
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


class EtsyRateLimitError(EtsyAPIError):
    """429 Too Many Requests."""
    pass


class EtsyAuthError(EtsyAPIError):
    """401/403 Authentication failure."""
    pass


class EtsyNotFoundError(EtsyAPIError):
    """404 Resource not found."""
    pass


class EtsyServerError(EtsyAPIError):
    """5xx Server error."""
    pass
