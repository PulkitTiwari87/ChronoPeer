"""Business logic. Services raise DomainError subclasses; main.py maps them to HTTP responses."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationFailed(DomainError):
    status_code = 422


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class Forbidden(DomainError):
    status_code = 403


class TooLarge(DomainError):
    status_code = 413


def get_or_404(db, model, pk, label):
    obj = db.get(model, pk)
    if obj is None:
        raise NotFound(f"{label} {pk} not found")
    return obj
