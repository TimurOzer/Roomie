from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, users, ilanlar, ws

app = FastAPI()

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme aşamasında tüm domainlere açık
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ları ekle
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(ilanlar.router, prefix="/ilanlar", tags=["İlanlar"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])

@app.get("/")
def root():
    return {"message": "Ev Arkadaşı Platformuna Hoş Geldiniz!"}
