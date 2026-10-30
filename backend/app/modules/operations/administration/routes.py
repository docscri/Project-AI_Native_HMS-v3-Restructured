"""Clinic settings, members and invites."""
from fastapi import APIRouter, Depends

from app.shared.auth import current_member, require_admin
from app.shared.db import get_db
from . import service
from .schema import Accept, Details, MemberUpdate, NewMember, ResetEmail, Rules

router = APIRouter(prefix="/api")


@router.put("/clinic")
def update_details(body: Details, me=Depends(require_admin), db=Depends(get_db)):
    return service.update_details(db, me, body)


@router.put("/clinic/rules")
def update_rules(body: Rules, me=Depends(require_admin), db=Depends(get_db)):
    return service.update_rules(db, me, body)


@router.get("/clinic")
def get_clinic(me=Depends(current_member), db=Depends(get_db)):
    return service.get_clinic(db, me)


@router.get("/members")
def list_members(me=Depends(current_member), db=Depends(get_db)):
    return service.list_members(db, me)


@router.post("/members")
def add_member(body: NewMember, me=Depends(require_admin), db=Depends(get_db)):
    return service.add_member(db, me, body)


@router.post("/members/{member_id}/invite")
def renew_invite(member_id: int, me=Depends(require_admin), db=Depends(get_db)):
    return service.renew_invite(db, me, member_id)


@router.post("/members/{member_id}/invite/email")
def email_invite(member_id: int, me=Depends(require_admin), db=Depends(get_db)):
    return service.email_invite(db, me, member_id)


@router.post("/members/{member_id}/reset-link")
def admin_reset_link(member_id: int, me=Depends(require_admin), db=Depends(get_db)):
    return service.admin_reset_link(db, me, member_id)


@router.post("/members/{member_id}/reset-link/email")
def email_reset_link(member_id: int, body: ResetEmail, me=Depends(require_admin), db=Depends(get_db)):
    return service.email_reset_link(db, me, member_id, body.code)


@router.patch("/members/{member_id}")
def update_member(member_id: int, body: MemberUpdate, me=Depends(require_admin), db=Depends(get_db)):
    return service.update_member(db, me, member_id, body)


@router.delete("/members/{member_id}")
def remove_member(member_id: int, me=Depends(require_admin), db=Depends(get_db)):
    return service.remove_member(db, me, member_id)


@router.get("/invites/{code}")
def view_invite(code: str, db=Depends(get_db)):
    return service.view_invite(db, code)


@router.post("/invites/accept")
def accept_invite(body: Accept, db=Depends(get_db)):
    return service.accept_invite(db, body.code, body.password)
