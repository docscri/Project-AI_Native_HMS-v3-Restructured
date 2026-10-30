"""Moved to app.modules.operations.{appointments,waitlist}; kept importable until callers move."""
from app.modules.operations.appointments.service import create_booking  # noqa: F401
from app.modules.operations.waitlist.service import add_to_waitlist  # noqa: F401
