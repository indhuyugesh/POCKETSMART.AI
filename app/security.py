import base64, hashlib, hmac, json, secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
from .database import get_db
from .models import User

def hash_password(password: str) -> str:
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,310000)
    return 'pbkdf2_sha256$310000$'+base64.urlsafe_b64encode(salt).decode()+ '$'+base64.urlsafe_b64encode(digest).decode()
def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_b64, digest_b64=stored.split('$')
        salt=base64.urlsafe_b64decode(salt_b64.encode()); expected=base64.urlsafe_b64decode(digest_b64.encode())
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,int(rounds))
        return hmac.compare_digest(actual,expected)
    except Exception: return False

def _b64(v: bytes)->str: return base64.urlsafe_b64encode(v).rstrip(b'=').decode()
def _unb64(s: str)->bytes: return base64.urlsafe_b64decode(s+'='*((4-len(s)%4)%4))
def create_access_token(username: str, expires_delta=None) -> str:
    exp=int((datetime.now(timezone.utc)+(expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))).timestamp())
    header=_b64(json.dumps({'alg':'HS256','typ':'JWT'},separators=(',',':')).encode()); payload=_b64(json.dumps({'sub':username,'exp':exp},separators=(',',':')).encode())
    sig=_b64(hmac.new(SECRET_KEY.encode(),f'{header}.{payload}'.encode(),hashlib.sha256).digest()); return f'{header}.{payload}.{sig}'
def decode_token(token):
    h,p,s=token.split('.'); expected=_b64(hmac.new(SECRET_KEY.encode(),f'{h}.{p}'.encode(),hashlib.sha256).digest())
    if not hmac.compare_digest(s,expected): raise ValueError('bad signature')
    data=json.loads(_unb64(p));
    if int(data.get('exp',0))<int(datetime.now(timezone.utc).timestamp()): raise ValueError('expired')
    return data

def get_current_user(request: Request, db: Session=Depends(get_db)):
    token=request.cookies.get('access_token')
    if not token:
        auth=request.headers.get('Authorization','')
        if auth.lower().startswith('bearer '): token=auth[7:].strip()
    if not token: raise HTTPException(401,'Not authenticated')
    try: username=decode_token(token).get('sub')
    except Exception: raise HTTPException(401,'Invalid or expired token')
    user=db.query(User).filter(User.username==username).first()
    if not user: raise HTTPException(401,'User not found')
    return user
