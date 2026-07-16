from fastapi import APIRouter, Depends
from app.services.search_service import run_search
from app.auth import get_current_user
router = APIRouter()

@router.get("/search")
def search(q: str, user=Depends(get_current_user)):
    return run_search(q)
