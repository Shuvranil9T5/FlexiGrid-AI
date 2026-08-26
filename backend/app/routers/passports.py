from fastapi import APIRouter
from app.database import list_saved_passports
from app.schemas import FlexibilityPassport
from app.services.passport_service import store_passport
router = APIRouter(prefix="/api/passports", tags=["passports"])

@router.get("")
def list_passports(): return list_saved_passports()

@router.post("")
def save_passport(passport: FlexibilityPassport): return store_passport(passport.model_dump())

@router.put("/{pattern_id}")
def update_passport(pattern_id: str, passport: FlexibilityPassport):
    payload = passport.model_dump(); payload["pattern_id"] = pattern_id
    return store_passport(payload)
