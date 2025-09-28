from fastapi import APIRouter, HTTPException, status
from ..database import get_db
from ..models import UserProfile

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/profile", status_code=201)
async def save_profile(profile: UserProfile):
    """
    Salva o perfil localmente no banco (opcional: para histórico).
    """
    doc = {
        "name": profile.name,
        "avatar": profile.avatar,
        "created_at": __import__("datetime").datetime.utcnow(),
    }
    res = await get_db()["profiles"].insert_one(doc)
    return {"id": str(res.inserted_id), "name": profile.name, "avatar": profile.avatar}

@router.get("/profiles")
async def list_profiles():
    cursor = get_db()["profiles"].find().sort("created_at", -1).limit(50)
    profiles = []
    async for p in cursor:
        p["id"] = str(p["_id"])
        p.pop("_id", None)
        profiles.append(p)
    return {"profiles": profiles}
