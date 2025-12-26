import enum
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import RolPolzovatelya, Zakaz, PozitsiyaZakaza, Blyudo, StatusZakaza, Polzovatel
from schemas import ZakazCreate, ZakazOut, PozitsiyaZakazaBase, PozitsiyaZakazaOut
from auth import get_current_polzovatel
from typing import List

router = APIRouter(prefix="/zakazy", tags=["zakazy"])

def poluchit_ili_sozdat_korzinu(db: Session, polzovatel: Polzovatel) -> Zakaz:
    """Получает корзину пользователя или создаёт новую, если её нет"""
    zakaz = db.query(Zakaz).filter(
        Zakaz.polzovatel_id == polzovatel.id,
        Zakaz.status == StatusZakaza.v_korzine
    ).first()

    if not zakaz:
        zakaz = Zakaz(polzovatel_id=polzovatel.id, status=StatusZakaza.v_korzine, summa=0.0)
        db.add(zakaz)
        db.commit()
        db.refresh(zakaz)

    # Обновляем сумму на основе актуальных позиций
    db.refresh(zakaz)
    zakaz.summa = sum(
        poz.cena_na_moment * poz.kolichestvo for poz in zakaz.pozitsii
    )
    db.commit()
    return zakaz


@router.get("/korzina", response_model=ZakazOut)
def poluchit_korzinu(db: Session = Depends(get_db), curr: Polzovatel = Depends(get_current_polzovatel)):
    """Просмотр текущей корзины"""
    return poluchit_ili_sozdat_korzinu(db, curr)


@router.post("/korzina/dobavit", response_model=ZakazOut)
def dobavit_v_korzinu(
    poz: PozitsiyaZakazaBase,
    db: Session = Depends(get_db),
    curr: Polzovatel = Depends(get_current_polzovatel)
):
    """Добавить блюдо в корзину (или увеличить количество, если уже есть)"""
    zakaz = poluchit_ili_sozdat_korzinu(db, curr)

    blyudo = db.query(Blyudo).filter(Blyudo.id == poz.blyudo_id).first()
    if not blyudo:
        raise HTTPException(status_code=404, detail="Blyudo ne najdeno")

    # Ищем существующую позицию с этим блюдом
    existing_poz = db.query(PozitsiyaZakaza).filter(
        PozitsiyaZakaza.zakaz_id == zakaz.id,
        PozitsiyaZakaza.blyudo_id == poz.blyudo_id
    ).first()

    if existing_poz:
        existing_poz.kolichestvo += poz.kolichestvo
    else:
        new_poz = PozitsiyaZakaza(
            zakaz_id=zakaz.id,
            blyudo_id=poz.blyudo_id,
            kolichestvo=poz.kolichestvo,
            cena_na_moment=blyudo.cena
        )
        db.add(new_poz)

    # Сохраняем изменения и обновляем сумму
    db.commit()
    db.refresh(zakaz)
    zakaz.summa = sum(poz.cena_na_moment * poz.kolichestvo for poz in zakaz.pozitsii)
    db.commit()

    return zakaz


@router.delete("/korzina/pozitsiya/{blyudo_id}")
def udalit_pozitsiyu_iz_korziny(
    blyudo_id: int,
    db: Session = Depends(get_db),
    curr: Polzovatel = Depends(get_current_polzovatel)
):
    """Удалить конкретное блюдо из корзины (все количество)"""
    zakaz = poluchit_ili_sozdat_korzinu(db, curr)

    poz = db.query(PozitsiyaZakaza).filter(
        PozitsiyaZakaza.zakaz_id == zakaz.id,
        PozitsiyaZakaza.blyudo_id == blyudo_id
    ).first()

    if not poz:
        raise HTTPException(status_code=404, detail="Eto blyudo ne v korzine")

    db.delete(poz)
    db.commit()

    # Пересчитываем сумму
    db.refresh(zakaz)
    zakaz.summa = sum(poz.cena_na_moment * poz.kolichestvo for poz in zakaz.pozitsii)
    db.commit()

    return {"status": "pozitsiya udalena", "novaya_summa": zakaz.summa}


@router.delete("/korzina/ochistit")
def ochistit_korzinu(
    db: Session = Depends(get_db),
    curr: Polzovatel = Depends(get_current_polzovatel)
):
    """Полностью очистить корзину"""
    zakaz = poluchit_ili_sozdat_korzinu(db, curr)

    # Удаляем все позиции
    db.query(PozitsiyaZakaza).filter(PozitsiyaZakaza.zakaz_id == zakaz.id).delete()
    zakaz.summa = 0.0
    db.commit()

    return {"status": "korzina ochishchena"}


@router.post("/oformit", response_model=ZakazOut)
def oformit_zakaz(
    data: ZakazCreate,
    db: Session = Depends(get_db),
    curr: Polzovatel = Depends(get_current_polzovatel)
):
    """Оформить заказ из корзины"""
    zakaz = poluchit_ili_sozdat_korzinu(db, curr)

    if zakaz.summa <= 0 or not zakaz.pozitsii:
        raise HTTPException(status_code=400, detail="Korzina pusta — dobavte blyuda")

    if not data.adres_dostavki:
        raise HTTPException(status_code=400, detail="Ukazhite adres dostavki")

    zakaz.status = StatusZakaza.oformlen
    zakaz.adres_dostavki = data.adres_dostavki
    db.commit()
    db.refresh(zakaz)

    return zakaz


@router.get("/", response_model=List[ZakazOut])
def poluchit_moi_zakazy(
    db: Session = Depends(get_db),
    curr: Polzovatel = Depends(get_current_polzovatel)
):
    """Получить список всех заказов пользователя (кроме корзины)"""
    return db.query(Zakaz).filter(
        Zakaz.polzovatel_id == curr.id,
        Zakaz.status != StatusZakaza.v_korzine
    ).order_by(Zakaz.data_sozdaniya.desc()).all()

def tolko_kurer(curr: Polzovatel = Depends(get_current_polzovatel)):
    if curr.rol != RolPolzovatelya.kurer:
        raise HTTPException(status_code=403, detail="Tolko kurer mozhet eto delat")
    return curr

# Список заказов, доступных для взятия в доставку (оформленные, но не взятые)
@router.get("/dostupnye-dlya-dostavki", response_model=List[ZakazOut])
def poluchit_dostupnye_zakazy(db: Session = Depends(get_db), kurer: Polzovatel = Depends(tolko_kurer)):
    return db.query(Zakaz).filter(
        Zakaz.status == StatusZakaza.oformlen,
        Zakaz.kurer_id.is_(None)
    ).all()

# Курьер берёт заказ в доставку
@router.post("/{zakaz_id}/vzyat-v-dostavku")
def vzyat_zakaz_v_dostavku(
    zakaz_id: int,
    db: Session = Depends(get_db),
    kurer: Polzovatel = Depends(tolko_kurer)
):
    zakaz = db.query(Zakaz).filter(Zakaz.id == zakaz_id).first()
    if not zakaz:
        raise HTTPException(404, "Zakaz ne najden")
    if zakaz.status != StatusZakaza.oformlen:
        raise HTTPException(400, "Zakaz uzhe v rabote ili otmenen")
    if zakaz.kurer_id is not None:
        raise HTTPException(400, "Zakaz uzhe vzyat drugim kurerom")

    zakaz.kurer_id = kurer.id
    zakaz.status = StatusZakaza.v_dostavke
    db.commit()
    db.refresh(zakaz)
    return {"status": "Zakaz vzyat v dostavku", "zakaz_id": zakaz_id}

# Курьер отмечает, что доставил заказ
@router.post("/{zakaz_id}/dostavlen-kurerom")
def otmetit_dostavleno_kurerom(
    zakaz_id: int,
    db: Session = Depends(get_db),
    kurer: Polzovatel = Depends(tolko_kurer)
):
    zakaz = db.query(Zakaz).filter(Zakaz.id == zakaz_id).first()
    if not zakaz:
        raise HTTPException(404, "Zakaz ne najden")
    if zakaz.kurer_id != kurer.id:
        raise HTTPException(403, "Eto ne vash zakaz")
    if zakaz.status != StatusZakaza.v_dostavke:
        raise HTTPException(400, "Zakaz ne v dostavke")

    zakaz.status = StatusZakaza.dostavlen  # Ждём подтверждения от пользователя
    db.commit()
    return {"status": "Zakaz otmechen kak dostavlennyj. Zhdem podtverzhdeniya ot klienta"}

# Пользователь подтверждает получение заказа → заказ завершён
@router.post("/{zakaz_id}/podtverdit-poluchenie")
def podtverdit_poluchenie(
    zakaz_id: int,
    db: Session = Depends(get_db),
    curr: Polzovatel = Depends(get_current_polzovatel)
):
    zakaz = db.query(Zakaz).filter(Zakaz.id == zakaz_id).first()
    if not zakaz:
        raise HTTPException(404, "Zakaz ne najden")
    if zakaz.polzovatel_id != curr.id:
        raise HTTPException(403, "Eto ne vash zakaz")
    if zakaz.status != StatusZakaza.dostavlen:
        raise HTTPException(400, "Zakaz eshche ne dostavlen ili uzhe podtverzhden")

    zakaz.podtverzhden_polzovatelem = True
    zakaz.status = StatusZakaza.zavershen  # Новый статус — полностью завершён
    db.commit()
    return {"status": "Spasibo! Zakaz uspeshno zavershen!"}

# Добавить новый статус в enum (в models.py)
class StatusZakaza(str, enum.Enum):
    v_korzine = "v_korzine"
    oformlen = "oformlen"
    v_dostavke = "v_dostavke"
    dostavlen = "dostavlen"        # Доставлен курьером, ждёт подтверждения
    zavershen = "zavershen"        # Полностью завершён (подтверждён пользователем)
    otmenen = "otmenen"

# Заказы, которые сейчас везёт этот курьер
@router.get("/moi-zakazy", response_model=List[ZakazOut])
def poluchit_moi_zakazy_kureru(db: Session = Depends(get_db), kurer: Polzovatel = Depends(tolko_kurer)):
    return db.query(Zakaz).filter(
        Zakaz.kurer_id == kurer.id,
        Zakaz.status.in_([StatusZakaza.v_dostavke, StatusZakaza.dostavlen])
    ).all()