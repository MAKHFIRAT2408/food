from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Restoran, Polzovatel
from schemas import RestoranCreate, RestoranOut
from auth import get_current_polzovatel

router = APIRouter(prefix="/restorany", tags=["restorany"])

@router.post("/", response_model=RestoranOut)
def sozdat_restoran(rest: RestoranCreate, db: Session = Depends(get_db), curr: Polzovatel = Depends(get_current_polzovatel)):
    new_rest = Restoran(**rest.model_dump())
    db.add(new_rest)
    db.commit()
    db.refresh(new_rest)
    return new_rest

@router.get("/", response_model=list[RestoranOut])
def poluchit_restorany(db: Session = Depends(get_db)):
    return db.query(Restoran).all()

@router.get("/{rest_id}", response_model=RestoranOut)
def poluchit_restoran(rest_id: int, db: Session = Depends(get_db)):
    rest = db.query(Restoran).filter(Restoran.id == rest_id).first()
    if not rest:
        raise HTTPException(404, "Restoran ne najden")
    return rest