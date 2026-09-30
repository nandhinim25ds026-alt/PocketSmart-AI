import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Depends, Form, File, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from models import RegisterUser, UserInDB, HomeBudgetInput, PartyBudgetInput, JewelryBudgetInput
from auth import (
    users_db, blacklisted_tokens,
    hash_password, authenticate_user, create_access_token,
    get_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from gemini_utils import get_home_recommendations, get_party_recommendations, get_jewelry_recommendations

app = FastAPI(title="PocketSmart: AI Budget Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory recommendation history: { username: [ {id, timestamp, type, input, result}, ... ] }
history_db: dict[str, list] = {}


def save_to_history(username: str, rec_type: str, input_data: dict, result: dict):
    history_db.setdefault(username, [])
    history_db[username].insert(0, {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "type": rec_type,
        "input": input_data,
        "result": result,
    })


# ---------------- Public pages ----------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    if username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    users_db[username] = UserInDB(
        username=username, email=email, hashed_password=hash_password(password)
    )
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@app.post("/logout")
async def logout(request: Request):
    token = await get_token(request)
    if token:
        blacklisted_tokens.add(token)
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


# ---------------- Protected pages ----------------
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    recent = history_db.get(current_user.username, [])[:5]
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": current_user, "recent": recent}
    )


@app.get("/home-planner", response_class=HTMLResponse)
async def home_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    return templates.TemplateResponse("home_planner.html", {"request": request, "user": current_user})


@app.post("/home-budget")
async def plan_home_budget(
    budget_input: HomeBudgetInput,
    current_user: UserInDB = Depends(get_current_active_user),
):
    result = get_home_recommendations(budget_input)
    save_to_history(current_user.username, "home", budget_input.dict(), result)
    return result


@app.get("/party-planner", response_class=HTMLResponse)
async def party_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    return templates.TemplateResponse("party_planner.html", {"request": request, "user": current_user})


@app.post("/party-budget")
async def plan_party_budget(
    budget_input: PartyBudgetInput,
    current_user: UserInDB = Depends(get_current_active_user),
):
    result = get_party_recommendations(budget_input)
    save_to_history(current_user.username, "party", budget_input.dict(), result)
    return result


@app.get("/jewelry-planner", response_class=HTMLResponse)
async def jewelry_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    return templates.TemplateResponse("jewelry_planner.html", {"request": request, "user": current_user})


@app.post("/jewelry-budget")
async def plan_jewelry_budget(
    total_budget: float = Form(...),
    occasion: str = Form(...),
    preferences: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: UserInDB = Depends(get_current_active_user),
):
    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        image_path = f"static/uploads/{uuid.uuid4()}{ext}"
        with open(image_path, "wb") as f:
            f.write(await image.read())

    budget_input = JewelryBudgetInput(
        total_budget=total_budget, occasion=occasion, preferences=preferences
    )
    result = get_jewelry_recommendations(budget_input, image_path)

    input_summary = budget_input.dict()
    input_summary["has_image"] = image_path is not None
    save_to_history(current_user.username, "jewelry", input_summary, result)
    return result


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    items = history_db.get(current_user.username, [])
    return templates.TemplateResponse(
        "history.html", {"request": request, "user": current_user, "history": items}
    )


if __name__ == "__main__":
    import uvicorn
    print("Starting PocketSmart: AI Budget Planner...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
