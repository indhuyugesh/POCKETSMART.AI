import json, uuid
from datetime import timedelta
from pathlib import Path
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import User, Recommendation
from .schemas import RegisterUser, HomeBudgetInput, PartyBudgetInput, JewelryBudgetInput
from .security import hash_password, verify_password, create_access_token, get_current_user
from .config import UPLOAD_DIR, ALLOWED_IMAGE_TYPES, MAX_UPLOAD_BYTES, ACCESS_TOKEN_EXPIRE_MINUTES
from .ai import home_recommendations, party_recommendations, jewelry_recommendations
BASE=Path(__file__).resolve().parent.parent
app=FastAPI(title="PocketSmart: AI Budget Planner", version="1.0.0")
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
templates=Jinja2Templates(directory=str(BASE/"templates"))
Base.metadata.create_all(bind=engine)

def page(request, name, **ctx): return templates.TemplateResponse(name,{"request":request,**ctx})
def save_history(db,user,kind,input_summary,result,image_filename=None):
    row=Recommendation(user_id=user.id,recommendation_type=kind,input_summary=input_summary,result_json=json.dumps(result),image_filename=image_filename); db.add(row); db.commit(); db.refresh(row); return row
@app.get("/health")
def health(): return {"status":"ok","service":"PocketSmart","ai_configured":bool(__import__('app.config',fromlist=['GOOGLE_API_KEY']).GOOGLE_API_KEY)}
@app.get("/",response_class=HTMLResponse)
def landing(request:Request): return page(request,"index.html")
@app.get("/login",response_class=HTMLResponse)
def login_page(request:Request): return page(request,"login.html")
@app.get("/register",response_class=HTMLResponse)
def register_page(request:Request): return page(request,"register.html")
@app.post("/register")
def register(username:str=Form(...),email:str=Form(...),full_name:str=Form(""),password:str=Form(...),db:Session=Depends(get_db)):
    if db.query(User).filter((User.username==username)|(User.email==email)).first(): return RedirectResponse("/register?error=Username+or+email+already+exists",303)
    db.add(User(username=username.strip(),email=email.strip().lower(),full_name=full_name.strip() or None,password_hash=hash_password(password))); db.commit()
    return RedirectResponse("/login?registered=1",303)
@app.post("/token")
def token(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    user=db.query(User).filter(User.username==username).first()
    if not user or not verify_password(password,user.password_hash): raise HTTPException(401,"Incorrect username or password")
    t=create_access_token(user.username,timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)); r=JSONResponse({"access_token":t,"token_type":"bearer"}); r.set_cookie("access_token",t,httponly=True,max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60,samesite="lax")
    return r
@app.post("/logout")
def logout():
    r=RedirectResponse("/",303); r.delete_cookie("access_token"); return r
@app.get("/dashboard",response_class=HTMLResponse)
def dashboard(request:Request,user=Depends(get_current_user),db:Session=Depends(get_db)):
    recent=db.query(Recommendation).filter(Recommendation.user_id==user.id).order_by(Recommendation.created_at.desc()).limit(3).all(); return page(request,"dashboard.html",user=user,recent=recent)
@app.get("/home-planner",response_class=HTMLResponse)
def home_page(request:Request,user=Depends(get_current_user)): return page(request,"home_planner.html",user=user)
@app.get("/party-planner",response_class=HTMLResponse)
def party_page(request:Request,user=Depends(get_current_user)): return page(request,"party_planner.html",user=user)
@app.get("/jewelry-planner",response_class=HTMLResponse)
def jewelry_page(request:Request,user=Depends(get_current_user)): return page(request,"jewelry_planner.html",user=user)
@app.post("/home-budget")
def home_budget(payload:HomeBudgetInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    result=home_recommendations(payload); save_history(db,user,"home",payload.model_dump_json(),result); return result
@app.post("/party-budget")
def party_budget(payload:PartyBudgetInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    result=party_recommendations(payload); save_history(db,user,"party",payload.model_dump_json(),result); return result
@app.post("/jewelry-budget")
async def jewelry_budget(total_budget:float=Form(...),occasion:str=Form(...),preferences:str=Form(""),image:UploadFile|None=File(None),user=Depends(get_current_user),db:Session=Depends(get_db)):
    image_bytes=None; image_name=None; mime=None
    if image:
        if image.content_type not in ALLOWED_IMAGE_TYPES: raise HTTPException(400,"Only JPG, PNG or WEBP images are supported")
        image_bytes=await image.read()
        if len(image_bytes)>MAX_UPLOAD_BYTES: raise HTTPException(400,"Image must be 5 MB or smaller")
        image_name=f"{uuid.uuid4().hex}{Path(image.filename or '').suffix.lower()}"; (UPLOAD_DIR/image_name).write_bytes(image_bytes); mime=image.content_type
    payload=JewelryBudgetInput(total_budget=total_budget,occasion=occasion,preferences=preferences or None)
    result=jewelry_recommendations(payload,image_bytes,mime); save_history(db,user,"jewelry",payload.model_dump_json(),result,image_name); return result
@app.get("/history",response_class=HTMLResponse)
def history_page(request:Request,user=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.query(Recommendation).filter(Recommendation.user_id==user.id).order_by(Recommendation.created_at.desc()).all(); return page(request,"history.html",user=user,rows=rows)
@app.get("/api/recommendation-history")
def history_api(user=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.query(Recommendation).filter(Recommendation.user_id==user.id).order_by(Recommendation.created_at.desc()).all(); return [{"id":r.id,"timestamp":r.created_at.isoformat(),"type":r.recommendation_type,"input":r.input_summary} for r in rows]
@app.get("/recommendation-details/{recommendation_id}",response_class=HTMLResponse)
def details(request:Request,recommendation_id:int,user=Depends(get_current_user),db:Session=Depends(get_db)):
    r=db.query(Recommendation).filter(Recommendation.id==recommendation_id,Recommendation.user_id==user.id).first()
    if not r: raise HTTPException(404,"Recommendation not found")
    return page(request,"recommendation.html",user=user,row=r,result=json.loads(r.result_json))
@app.get("/api/recommendation-details/{recommendation_id}")
def details_api(recommendation_id:int,user=Depends(get_current_user),db:Session=Depends(get_db)):
    r=db.query(Recommendation).filter(Recommendation.id==recommendation_id,Recommendation.user_id==user.id).first()
    if not r: raise HTTPException(404,"Recommendation not found")
    return {"id":r.id,"timestamp":r.created_at.isoformat(),"type":r.recommendation_type,"input":json.loads(r.input_summary),"full_result":json.loads(r.result_json)}
@app.get("/session-info")
def session_info(user=Depends(get_current_user)): return {"username":user.username,"email":user.email}
