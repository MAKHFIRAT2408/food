from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from models import Polzovatel, RolPolzovatelya
from routers.blyuda_router import tolko_admin
from schemas import PolzovatelCreate, Token
from auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(polzovatel: PolzovatelCreate, db: Session = Depends(get_db)):
    if db.query(Polzovatel).filter(Polzovatel.username == polzovatel.username).first():
        raise HTTPException(status_code=400, detail="Polzovatel uzhe sushchestvuet")
    new_polz = Polzovatel(username=polzovatel.username, hashed_password=hash_password(polzovatel.password))
    db.add(new_polz)
    db.commit()
    token = create_access_token({"sub": polzovatel.username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    polz = db.query(Polzovatel).filter(Polzovatel.username == form_data.username).first()
    if not polz or not verify_password(form_data.password, polz.hashed_password):
        raise HTTPException(status_code=401, detail="Nepravilnyj login ili parol")
    token = create_access_token({"sub": polz.username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/set-role/{user_id}/{new_role}")
def naznachit_rol(
    user_id: int,
    new_role: RolPolzovatelya,
    db: Session = Depends(get_db),
    admin: Polzovatel = Depends(tolko_admin)
):
    polz = db.query(Polzovatel).filter(Polzovatel.id == user_id).first()
    if not polz:
        raise HTTPException(404, "Polzovatel ne najden")
    polz.rol = new_role
    db.commit()
    return {"status": "rol izmenena", "polzovatel": polz.username, "novaya_rol": new_role.value}