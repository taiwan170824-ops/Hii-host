from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.database import get_db
from app.services.auth import verify_password, create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(req: LoginRequest):
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token({"sub": user["username"], "id": user["id"]})
        return {"access_token": token, "token_type": "bearer", "username": user["username"]}
    finally:
        db.close()

@router.post("/change-password")
def change_password(data: dict, user=None):
    # Handled in main routes with auth dependency
    pass
