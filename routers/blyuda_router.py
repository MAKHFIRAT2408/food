import os
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from models import Blyudo, Restoran, Polzovatel, RolPolzovatelya
from schemas import BlyudoCreate, BlyudoOut, BlyudoUpdate
from auth import get_current_polzovatel

router = APIRouter(prefix="/blyuda", tags=["blyuda"])

# Папка для хранения фото блюд
UPLOAD_DIR = "static/blyuda"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def tolko_admin(curr: Polzovatel = Depends(get_current_polzovatel)):
    if curr.rol != RolPolzovatelya.admin:
        raise HTTPException(status_code=403, detail="Tolko admin mozhet eto delat")
    return curr


@router.post("/", response_model=BlyudoOut)
async def sozdat_blyudo(
    nazvanie: str = Form(...),
    opisanie: Optional[str] = Form(None),
    cena: float = Form(...),
    restoran_id: int = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin: Polzovatel = Depends(tolko_admin)
):
    """Создание нового блюда (только админ)"""
    # Проверка существования ресторана
    restoran = db.query(Restoran).filter(Restoran.id == restoran_id).first()
    if not restoran:
        raise HTTPException(status_code=404, detail="Restoran ne najden")

    new_blyudo = Blyudo(
        nazvanie=nazvanie,
        opisanie=opisanie,
        cena=cena,
        restoran_id=restoran_id
    )
    db.add(new_blyudo)
    db.commit()
    db.refresh(new_blyudo)

    # Обработка фото, если загружено
    if foto:
        file_extension = foto.filename.split(".")[-1] if "." in foto.filename else "jpg"
        filename = f"{new_blyudo.id}_{uuid4().hex}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            content = await foto.read()
            buffer.write(content)

        new_blyudo.foto_url = f"/static/blyuda/{filename}"
        db.commit()
        db.refresh(new_blyudo)

    return new_blyudo


@router.get("/", response_model=List[BlyudoOut])
def poluchit_blyuda(
    restoran_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Получить все блюда или блюда конкретного ресторана"""
    query = db.query(Blyudo)
    if restoran_id is not None:
        query = query.filter(Blyudo.restoran_id == restoran_id)
    return query.all()


@router.get("/{blyudo_id}", response_model=BlyudoOut)
def poluchit_blyudo_po_id(
    blyudo_id: int,
    db: Session = Depends(get_db)
):
    """Получить одно блюдо по ID"""
    blyudo = db.query(Blyudo).filter(Blyudo.id == blyudo_id).first()
    if not blyudo:
        raise HTTPException(status_code=404, detail="Blyudo ne najdeno")
    return blyudo


@router.put("/{blyudo_id}", response_model=BlyudoOut)
async def obnovit_blyudo(
    blyudo_id: int,
    nazvanie: Optional[str] = Form(None),
    opisanie: Optional[str] = Form(None),
    cena: Optional[float] = Form(None),
    restoran_id: Optional[int] = Form(None),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin: Polzovatel = Depends(tolko_admin)
):
    """Полное обновление блюда (все поля + фото) — только админ"""
    blyudo = db.query(Blyudo).filter(Blyudo.id == blyudo_id).first()
    if not blyudo:
        raise HTTPException(status_code=404, detail="Blyudo ne najdeno")

    if nazvanie is not None:
        blyudo.nazvanie = nazvanie
    if opisanie is not None:
        blyudo.opisanie = opisanie
    if cena is not None:
        if cena < 0:
            raise HTTPException(status_code=400, detail="Cena ne mozhet byt otricatelnoj")
        blyudo.cena = cena
    if restoran_id is not None:
        restoran = db.query(Restoran).filter(Restoran.id == restoran_id).first()
        if not restoran:
            raise HTTPException(status_code=404, detail="Restoran s takim ID ne najden")
        blyudo.restoran_id = restoran_id

    # Замена фото, если загружено новое
    if foto:
        file_extension = foto.filename.split(".")[-1] if "." in foto.filename else "jpg"
        filename = f"{blyudo_id}_{uuid4().hex}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            content = await foto.read()
            buffer.write(content)

        blyudo.foto_url = f"/static/blyuda/{filename}"

    db.commit()
    db.refresh(blyudo)
    return blyudo