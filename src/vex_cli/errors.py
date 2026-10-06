class AppException(Exception):
    """Base exception for all application errors"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseError(AppException):
    """Database operation errors"""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class NoProjectActiveError(AppException):
    """Normal client state — no project selected yet (not a server fault)."""

    def __init__(self, message: str = "No active project — select a project first"):
        super().__init__(message, status_code=409)


class ProxyException(AppException):
    """Proxy operation errors"""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class NotFoundError(AppException):
    """Resource not found; `message` must name the missing resource."""

    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class RequestValidationError(AppException):
    """Business logic validation errors. """

    def __init__(self, message: str):
        super().__init__(message, status_code=422)
