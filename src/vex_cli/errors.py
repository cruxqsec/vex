class AppException(Exception):
    """Base exception for all application errors"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DatabaseError(AppException):
    """Database operation errors"""

    def __init__(self, message: str):
        super().__init__(message)

class ConflictError(AppException):
     """Conflict errors from operations for creating objects"""

     def __init__(self, message: str):
         super().__init__(message)

class DirectoryError(AppException):
     def __init__(self, message: str):
         super().__init__(message)


class NoProjectActiveError(AppException):
    """No project selected yet."""

    def __init__(self, message: str = "No active project — select a project first"):
        super().__init__(message)

class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str):
        super().__init__(message)

class VexClientDisconnectEvent(Exception):
    pass
