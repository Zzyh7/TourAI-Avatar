"""员工账号管理"""
import hashlib, secrets
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.schema import StaffAccount

router = APIRouter(prefix="/api/admin/staff", tags=["员工管理"])

class StaffCreate(BaseModel):
    account: str
    password: str

class StaffUpdate(BaseModel):
    account: str | None = None
    password: str | None = None
    active: int | None = None

@router.get("")
def list_staff(db: Session = Depends(get_db)):
    return [{"id": s.id, "account": s.account, "active": s.active} for s in db.query(StaffAccount).all()]

@router.post("")
def create_staff(data: StaffCreate, db: Session = Depends(get_db)):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((data.password + salt).encode()).hexdigest()
    s = StaffAccount(account=data.account, password_hash=h, salt=salt)
    db.add(s); db.commit()
    return {"message": "ok", "id": s.id}

@router.put("/{sid}")
def update_staff(sid: int, data: StaffUpdate, db: Session = Depends(get_db)):
    s = db.query(StaffAccount).filter(StaffAccount.id == sid).first()
    if not s: return {"message": "not found"}
    if data.account: s.account = data.account
    if data.password:
        s.salt = secrets.token_hex(16)
        s.password_hash = hashlib.sha256((data.password + s.salt).encode()).hexdigest()
    if data.active is not None: s.active = data.active
    db.commit(); return {"message": "ok"}

@router.delete("/{sid}")
def delete_staff(sid: int, db: Session = Depends(get_db)):
    db.query(StaffAccount).filter(StaffAccount.id == sid).delete()
    db.commit(); return {"message": "ok"}
