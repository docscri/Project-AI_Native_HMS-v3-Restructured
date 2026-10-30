"""Services raise these; one handler turns them into HTTP replies with the short message."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    status = 404


class Conflict(DomainError):
    status = 409


class Invalid(DomainError):
    status = 422


class Forbidden(DomainError):
    status = 403


def install(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    def domain(request: Request, exc: DomainError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.exception_handler(ValueError)
    def bad_value(request: Request, exc: ValueError):   # a malformed date or number is a 422, not a 500
        return JSONResponse({"detail": "Check the dates."}, status_code=422)
