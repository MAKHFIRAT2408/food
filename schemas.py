from pydantic import BaseModel
from datetime import datetime
from typing import List

class PolzovatelCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class PolzovatelOut(BaseModel):
    id: int
    username: str
    rol: str

    class Config:
        from_attributes = True

class RestoranBase(BaseModel):
    nazvanie: str
    adres: str
    opisanie: str | None = None

class RestoranCreate(RestoranBase):
    pass

class RestoranOut(RestoranBase):
    id: int

    class Config:
        from_attributes = True

class BlyudoBase(BaseModel):
    nazvanie: str
    opisanie: str | None = None
    cena: float
    restoran_id: int

class BlyudoCreate(BlyudoBase):
    pass

class BlyudoOut(BlyudoBase):
    id: int
    foto_url: str | None = None

    class Config:
        from_attributes = True

class BlyudoUpdate(BaseModel):
    nazvanie: str | None = None
    opisanie: str | None = None
    cena: float | None = None
    restoran_id: int | None = None

class PozitsiyaZakazaBase(BaseModel):
    blyudo_id: int
    kolichestvo: int = 1

class PozitsiyaZakazaOut(PozitsiyaZakazaBase):
    id: int
    cena_na_moment: float
    blyudo: BlyudoOut

    class Config:
        from_attributes = True

class ZakazCreate(BaseModel):
    adres_dostavki: str | None = None

class ZakazOut(BaseModel):
    id: int
    status: str
    data_sozdaniya: datetime
    adres_dostavki: str | None
    summa: float
    podtverzhden_polzovatelem: bool
    polzovatel_id: int
    kurer_id: int | None = None
    pozitsii: List[PozitsiyaZakazaOut] = []

    class Config:
        from_attributes = True