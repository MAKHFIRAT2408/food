from sqlalchemy import Boolean, Column, Integer, String, Text, Float, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base

class RolPolzovatelya(str, enum.Enum):
    polzovatel = "polzovatel"
    admin = "admin"
    kurer = "kurer"

class Polzovatel(Base):
    __tablename__ = "polzovateli"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    rol = Column(Enum(RolPolzovatelya), default=RolPolzovatelya.polzovatel)

    # Заказы, которые сделал этот пользователь (как клиент)
    zakazy_kak_klient = relationship(
        "Zakaz",
        back_populates="polzovatel",
        foreign_keys="Zakaz.polzovatel_id"  # ← Явно указываем, какой FK
    )

    # Заказы, которые доставляет этот пользователь (как курьер)
    zakazy_kak_kurer = relationship(
        "Zakaz",
        back_populates="kurer",
        foreign_keys="Zakaz.kurer_id"       # ← Явно указываем другой FK
    )

class Restoran(Base):
    __tablename__ = "restorany"

    id = Column(Integer, primary_key=True, index=True)
    nazvanie = Column(String, index=True)
    adres = Column(String)
    opisanie = Column(Text)

    blyuda = relationship("Blyudo", back_populates="restoran")

class Blyudo(Base):
    __tablename__ = "blyuda"

    id = Column(Integer, primary_key=True, index=True)
    nazvanie = Column(String, index=True)
    opisanie = Column(Text)
    cena = Column(Float, nullable=False)
    foto_url = Column(String, nullable=True)
    restoran_id = Column(Integer, ForeignKey("restorany.id"))

    restoran = relationship("Restoran", back_populates="blyuda")
    pozitsii_zakaza = relationship("PozitsiyaZakaza", back_populates="blyudo")

class StatusZakaza(str, enum.Enum):
    v_korzine = "v_korzine"
    oformlen = "oformlen"
    v_dostavke = "v_dostavke"
    dostavlen = "dostavlen"
    otmenen = "otmenen"

class Zakaz(Base):
    __tablename__ = "zakazy"

    id = Column(Integer, primary_key=True, index=True)
    polzovatel_id = Column(Integer, ForeignKey("polzovateli.id"), nullable=False)
    kurer_id = Column(Integer, ForeignKey("polzovateli.id"), nullable=True)
    status = Column(Enum(StatusZakaza), default=StatusZakaza.v_korzine)
    data_sozdaniya = Column(DateTime, default=datetime.utcnow)
    adres_dostavki = Column(String, nullable=True)
    summa = Column(Float, default=0.0)
    podtverzhden_polzovatelem = Column(Boolean, default=False)

    # Клиент, который сделал заказ
    polzovatel = relationship("Polzovatel", back_populates="zakazy_kak_klient", foreign_keys=[polzovatel_id])

    # Курьер, который доставляет
    kurer = relationship("Polzovatel", back_populates="zakazy_kak_kurer", foreign_keys=[kurer_id])

    pozitsii = relationship("PozitsiyaZakaza", back_populates="zakaz")

class PozitsiyaZakaza(Base):
    __tablename__ = "pozitsii_zakaza"

    id = Column(Integer, primary_key=True, index=True)
    zakaz_id = Column(Integer, ForeignKey("zakazy.id"))
    blyudo_id = Column(Integer, ForeignKey("blyuda.id"))
    kolichestvo = Column(Integer, default=1)
    cena_na_moment = Column(Float)  # цена блюда на момент добавления

    zakaz = relationship("Zakaz", back_populates="pozitsii")
    blyudo = relationship("Blyudo", back_populates="pozitsii_zakaza")