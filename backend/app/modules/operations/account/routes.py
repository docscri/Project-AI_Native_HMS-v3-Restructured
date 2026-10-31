"""Login, logout, passwords, /api/me and owner onboarding."""
from fastapi import APIRouter, Depends, Header

from app.shared.auth import current_member, require_admin
from app.shared.db import get_db

from . import service
from .schema import ChangePassword, Forgot, Login, MyProfile, Owner, OwnerEdit, Reset


router = APIRouter(prefix="/api")


def bearer(authorization: str) -> str:
    return authorization.removeprefix("Bearer ").strip()


@router.post("/auth/login")
def login(body: Login, db=Depends(get_db)):
    return service.login(db, body.email, body.password)


@router.post("/auth/logout")
def logout(authorization: str = Header(default=""), db=Depends(get_db)):
    return service.logout(db, bearer(authorization))


@router.post("/auth/change-password")
def change_password(body: ChangePassword, authorization: str = Header(default=""), me=Depends(current_member), db=Depends(get_db)):
    return service.change_password(db, me, body.current, body.new, bearer(authorization))


@router.post("/auth/forgot")
def forgot(body: Forgot, db=Depends(get_db)):
    return service.forgot(db, body.email)


@router.post("/auth/reset")
def reset_password(body: Reset, db=Depends(get_db)):
    return service.reset_password(db, body.code, body.password)


@router.get("/me")
def me_(me=Depends(current_member), db=Depends(get_db)):
    return service.me(db, me)


@router.put("/me")
def edit_me(body: MyProfile, me=Depends(current_member), db=Depends(get_db)):
    return service.edit_me(db, me, body)


@router.post("/onboarding/owner")
def create_owner(body: Owner, db=Depends(get_db)):
    return service.create_owner(db, body)


@router.put("/onboarding/owner")
def edit_owner(body: OwnerEdit, me=Depends(current_member), db=Depends(get_db)):
    return service.edit_owner(db, me, body)


@router.post("/onboarding/finish")
def finish(me=Depends(require_admin), db=Depends(get_db)):
    return service.finish(db, me)
