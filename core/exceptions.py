class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DailyLimitExceeded(AppException):
    def __init__(self):
        super().__init__(message="You have reached your daily debate limit. Upgrade to premium for unlimited debates.", status_code=429)


class DebateNotFound(AppException):
    def __init__(self):
        super().__init__(message="Debate not found", status_code=404)


class AudioTooLarge(AppException):
    def __init__(self):
        super().__init__(message="Audio file too large. Maximum 5MB allowed.", status_code=413)


class MaxTurnsExceeded(AppException):
    def __init__(self):
        super().__init__(message="Maximum debate turns reached. Please end the debate.", status_code=400)


class SarvamAPIError(AppException):
    def __init__(self, message: str = "AI service error"):
        super().__init__(message=message, status_code=502)
