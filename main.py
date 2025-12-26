from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import Base, engine
from routers import auth_router, restorany_router, blyuda_router, zakazy_router

app = FastAPI(title="Food Delivery API")

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router.router)
app.include_router(restorany_router.router)
app.include_router(blyuda_router.router)
app.include_router(zakazy_router.router)

@app.get("/")
def root():
    return {"message": "Dobro pozhalovat v API dostavki edy!"}