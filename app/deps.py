# app/deps.py
import os
import secrets

from fastapi import Depends, HTTPException, Header, status
from fastapi import Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session
from app.db.oracle import get_db
from app.api.auth.auth import SECRET_KEY, ALGORITHM
from app.models.models import AppUser

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        mobile_number: str = payload.get("sub")
        if mobile_number is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    # Ensure the user still exists in the database
    user = db.query(AppUser).filter(AppUser.mob == mobile_number).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user


def require_agent_key(x_api_key: str = Header(default="")):
    expected = os.getenv("AGENT_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")