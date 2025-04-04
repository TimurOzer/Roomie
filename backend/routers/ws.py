from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from auth_router import oauth2_scheme, fake_users_db
from users_router import get_current_username, user_limits, reset_limits_if_needed
from ws_router import bildirim_gonder

router = APIRouter()

ilan_db = []
interactions = {}  # Kullanıcının tepki verdiği ilanlar
matchler = set()   # Karşılıklı eşleşmeler (tuple olarak)

class Ilan(BaseModel):
    id: int
    ilan_sahibi: str
    sehir: str
    ilce: str
    oda_sayisi: str
    sigara: bool
    evcil: bool
    tarih: datetime

class IlanInput(BaseModel):
    sehir: str
    ilce: str
    oda_sayisi: str
    sigara: bool
    evcil: bool

@router.post("/ekle", response_model=Ilan)
async def ilan_ekle(ilan: IlanInput, username: str = Depends(get_current_username)):
    yeni_ilan = Ilan(
        id=len(ilan_db) + 1,
        ilan_sahibi=username,
        sehir=ilan.sehir,
        ilce=ilan.ilce,
        oda_sayisi=ilan.oda_sayisi,
        sigara=ilan.sigara,
        evcil=ilan.evcil,
        tarih=datetime.utcnow()
    )
    ilan_db.append(yeni_ilan)
    return yeni_ilan

@router.get("/liste", response_model=List[Ilan])
async def ilan_listele():
    return ilan_db[::-1]

@router.get("/next", response_model=Optional[Ilan])
async def siradaki_ilan(username: str = Depends(get_current_username)):
    kullanici_inter = interactions.get(username, set())
    for ilan in ilan_db:
        if ilan.ilan_sahibi != username and ilan.id not in kullanici_inter:
            return ilan
    return None

@router.post("/tepki")
async def ilan_tepki(ilan_id: int, tepki: str, username: str = Depends(get_current_username)):
    reset_limits_if_needed(username)
    if tepki not in ["cay", "kahve", "carpi"]:
        raise HTTPException(status_code=400, detail="Geçersiz tepki türü")

    ilan = next((i for i in ilan_db if i.id == ilan_id), None)
    if not ilan:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    if ilan.ilan_sahibi == username:
        raise HTTPException(status_code=400, detail="Kendi ilanına tepki veremezsin")

    limits = user_limits[username]
    if tepki == "cay" and limits['cay'] <= 0:
        raise HTTPException(status_code=400, detail="Günlük çay hakkın tükendi")
    if tepki == "kahve" and limits['kahve'] <= 0:
        raise HTTPException(status_code=400, detail="Günlük kahve hakkın tükendi")

    if tepki == "cay":
        user_limits[username]['cay'] -= 1
    elif tepki == "kahve":
        user_limits[username]['kahve'] -= 1

    if username not in interactions:
        interactions[username] = set()
    interactions[username].add(ilan_id)

    mesaj = f"{username} sana bir '{tepki}' gönderdi! Onaylamak için /ilanlar/onayla endpoint'ini kullanabilirsin."
    await bildirim_gonder(ilan.ilan_sahibi, mesaj)

    return {"message": f"'{tepki}' tepkisi verildi", "kalan_cay": user_limits[username]['cay'], "kalan_kahve": user_limits[username]['kahve']}

@router.post("/onayla")
async def teklif_onayla(kullanici: str, ilan_id: int, username: str = Depends(get_current_username)):
    ilan = next((i for i in ilan_db if i.id == ilan_id), None)
    if not ilan:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    if ilan.ilan_sahibi != username:
        raise HTTPException(status_code=403, detail="Bu ilana sahip değilsiniz")

    if kullanici not in fake_users_db:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    match = tuple(sorted([username, kullanici]))
    if match in matchler:
        return {"message": "Zaten eşleştiniz."}

    matchler.add(match)
    await bildirim_gonder(kullanici, f"🎉 {username} teklifini onayladı! Artık mesajlaşabilirsiniz.")
    await bildirim_gonder(username, f"🎉 {kullanici} ile eşleştiniz. Mesajlaşma aktif!")
    return {"message": "Teklif onaylandı, eşleşme oluşturuldu."}
