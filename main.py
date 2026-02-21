from fastapi import FastAPI, Request, Form, Query, Depends, Response, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select
from dotenv import load_dotenv
import os
import json
import time

from core.database import create_db_and_tables, get_session
from models.database import User, SearchHistory, Favorite
from services.social_api import SocialAPIWrapper
from services.ai_agent import AIAgent
from services import rapidapi_service
from services import auth
from services.cache import app_cache

load_dotenv()

app = FastAPI(title="Nocta Trends Pro")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Initialize default admin
    with next(get_session()) as session:
        auth.init_admin_user(session)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Custom Jinja2 filters
def format_num(value):
    try:
        n = int(value)
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.1f}K"
        return str(n)
    except (TypeError, ValueError): return str(value)

templates.env.filters["format_num"] = format_num

social_api = SocialAPIWrapper()
ai_agent = AIAgent()

# --- Auth Decorator Dependency ---
def get_user_from_cookie(request: Request, session: Session = Depends(get_session)):
    return auth.get_current_user(request, session)

def get_auth_context(request: Request, user: User):
    """Helper to return consistent auth dict for templates"""
    return {
        "request": request,
        "user": user,
        "is_authenticated": user is not None
    }

# --- Main Page ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: User = Depends(get_user_from_cookie)):
    return templates.TemplateResponse("index.html", get_auth_context(request, user))

# --- Auth Routes ---
@app.post("/auth/login")
async def login(request: Request, response: Response, email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not auth.verify_password(password, user.password_hash):
        return JSONResponse({"status": "error", "message": "Неверный email или пароль"}, status_code=401)
    
    res = JSONResponse({"status": "ok", "user": {"name": user.name, "tokens": user.tokens, "role": user.role}})
    auth.create_session(user.id, res)
    return res

@app.post("/auth/register")
async def register(request: Request, response: Response, email: str = Form(...), name: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        return JSONResponse({"status": "error", "message": "Email уже занят"}, status_code=400)
    
    new_user = User(email=email, name=name, password_hash=auth.hash_password(password), tokens=100)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    res = JSONResponse({"status": "ok", "user": {"name": new_user.name, "tokens": new_user.tokens, "role": new_user.role}})
    auth.create_session(new_user.id, res)
    return res

@app.post("/auth/logout")
@app.get("/auth/logout")
async def logout(request: Request, response: Response):
    res = JSONResponse({"status": "ok"})
    auth.destroy_session(request, res)
    if request.method == "GET":
        from fastapi.responses import RedirectResponse
        redir = RedirectResponse(url="/", status_code=302)
        auth.destroy_session(request, redir)
        return redir
    return res

# --- Home: Trending Feed (Банк идей) ---
@app.get("/api/home", response_class=HTMLResponse)
async def home_feed(request: Request, user: User = Depends(get_user_from_cookie)):
    ctx = get_auth_context(request, user)
    return templates.TemplateResponse("partials/home.html", ctx)

@app.get("/api/home/feed", response_class=HTMLResponse)
async def home_feed_data(request: Request, page: int = Query(1), user: User = Depends(get_user_from_cookie)):
    if not user: return HTMLResponse("<div class='auth-required'>Пожалуйста, войдите в систему</div>")
    
    cache_key = f"home_feed_p{page}"
    videos = app_cache.get(cache_key)
    
    if not videos:
        import random
        trending_keywords = ["travel", "fitness", "fashion", "food", "luxury", "tech", "business", "motivation"]
        keyword = random.choice(trending_keywords)
        videos = await social_api.search_trends(keyword, "all", "views")
        random.shuffle(videos)
        app_cache.set(cache_key, videos, ttl_seconds=600) # Cache for 10 min
        
        # Deduct 1 token per feed load
        if len(videos) > 0 and page == 1:
            auth.deduct_tokens(user, 1, next(get_session()))

    ctx = get_auth_context(request, user)
    ctx.update({"videos": videos, "page": page, "section": "home"})
    return templates.TemplateResponse("partials/video_grid.html", ctx)

# --- Search (Поиск по слову) ---
@app.get("/api/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = "",
    timeframe: str = "all",
    sort_by: str = "views",
    page: int = Query(1),
    user: User = Depends(get_user_from_cookie),
    db: Session = Depends(get_session)
):
    if not user: return HTMLResponse("<div class='auth-required'>Пожалуйста, войдите в систему</div>")
    
    if not q:
        ctx = get_auth_context(request, user)
        ctx.update({"videos": [], "page": page, "section": "search", "empty_msg": "Введите запрос для поиска"})
        return templates.TemplateResponse("partials/search_view.html", ctx)
        
    cache_key = f"search_{q}_{timeframe}_{sort_by}_p{page}"
    videos = app_cache.get(cache_key)
    
    if not videos:
        videos = await social_api.search_trends(q, timeframe, sort_by)
        app_cache.set(cache_key, videos, ttl_seconds=300) # Cache 5 mins
        
        # Log to DB history & deduct 2 tokens for a search
        if videos and page == 1:
            previews = json.dumps([v.get("thumbnail_url") for v in videos[:4]])
            history = SearchHistory(user_id=user.id, query=q, results_count=len(videos), preview_thumbnails=previews)
            db.add(history)
            auth.deduct_tokens(user, 2, db)
            db.commit()

    ctx = get_auth_context(request, user)
    ctx.update({"videos": videos, "page": page, "section": "search", "query": q})
    return templates.TemplateResponse("partials/search_view.html" if page == 1 else "partials/video_grid.html", ctx)

# --- Anomalous Videos (Аномальные видео) ---
@app.get("/api/anomalous-page", response_class=HTMLResponse)
async def anomalous_page(request: Request, user: User = Depends(get_user_from_cookie)):
    return templates.TemplateResponse("partials/anomalous.html", get_auth_context(request, user))

@app.get("/api/anomalous", response_class=HTMLResponse)
async def anomalous(
    request: Request,
    sort_by: str = "anomaly",
    timeframe: str = "3d",
    page: int = Query(1),
    user: User = Depends(get_user_from_cookie),
    db: Session = Depends(get_session)
):
    if not user: return HTMLResponse("<div class='auth-required'>Пожалуйста, войдите в систему</div>")
    
    cache_key = f"anomalous_{timeframe}_{sort_by}_p{page}"
    videos = app_cache.get(cache_key)
    
    if not videos:
        videos = await social_api.search_trends("viral trending wow epic", timeframe, "views")
        for v in videos:
            likes = v.get("likes", 1) or 1
            views = v.get("views", 0) or 0
            v["anomaly_score"] = round(views / max(likes, 1), 1)
            
        if sort_by == "anomaly":
            videos.sort(key=lambda x: x.get("anomaly_score", 0), reverse=True)
        elif sort_by == "views":
            videos.sort(key=lambda x: x.get("views", 0), reverse=True)
            
        app_cache.set(cache_key, videos, ttl_seconds=600)
        auth.deduct_tokens(user, 3, db) # Anomalous scan is expensive

    ctx = get_auth_context(request, user)
    ctx.update({"videos": videos, "page": page, "section": "anomalous"})
    return templates.TemplateResponse("partials/video_grid.html", ctx)

# --- Profile Analysis ---
@app.get("/api/profile-page", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(get_user_from_cookie)):
    return templates.TemplateResponse("partials/profile_page.html", get_auth_context(request, user))

@app.post("/api/analyze-profile", response_class=HTMLResponse)
async def analyze_profile(request: Request, username: str = Form(...), user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return HTMLResponse("Needs login")
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    clean_username = username.replace("@", "").strip()
    with ThreadPoolExecutor() as pool:
        videos = await loop.run_in_executor(pool, rapidapi_service.fetch_reels_from_account_sync, clean_username, None)
        
    total_views = sum(v.get("views", 0) for v in videos)
    avg_er = round(sum(v.get("engagement_rate", 0) for v in videos) / max(len(videos), 1), 2)
    
    auth.deduct_tokens(user, 5, db) # Profile scan

    ctx = get_auth_context(request, user)
    ctx.update({"username": username, "videos": videos, "total_views": total_views, "avg_er": avg_er, "video_count": len(videos)})
    return templates.TemplateResponse("partials/profile_result.html", ctx)

# --- Admin Panel ---
@app.get("/api/admin-page", response_class=HTMLResponse)
async def admin_page(request: Request, user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user or user.role != "admin":
        return HTMLResponse("<div class='auth-required'>Доступ запрещен. Только для администраторов.</div>")
    
    users = db.exec(select(User)).all()
    searches = db.exec(select(SearchHistory)).all()
    
    ctx = get_auth_context(request, user)
    ctx.update({"total_users": len(users), "total_searches": len(searches), "users": users})
    return templates.TemplateResponse("partials/admin_page.html", ctx)

@app.post("/api/admin/add-tokens")
async def admin_add_tokens(user_id: int = Form(...), amount: int = Form(...), request: Request = None, user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user or user.role != "admin": return JSONResponse({"error": "Unauthorized"}, status_code=403)
    target = db.get(User, user_id)
    if target:
        target.tokens += amount
        db.add(target)
        db.commit()
    return JSONResponse({"status": "ok"})

# --- Favorites ---
@app.get("/api/favorites-page", response_class=HTMLResponse)
async def favorites_page(request: Request, user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return HTMLResponse("Needs login")
    favs = db.exec(select(Favorite).where(Favorite.user_id == user.id)).all()
    videos = [json.loads(f.video_data) for f in favs]
    ctx = get_auth_context(request, user)
    ctx.update({"favorites": videos})
    return templates.TemplateResponse("partials/favorites_page.html", ctx)

@app.post("/api/favorites/add")
async def favorites_add(request: Request, user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    video = data.get("video", {})
    if video:
        existing = db.exec(select(Favorite).where(Favorite.user_id == user.id, Favorite.video_url == video.get("video_url")).limit(1)).first()
        if not existing:
            new_fav = Favorite(user_id=user.id, video_url=video.get("video_url"), video_data=json.dumps(video))
            db.add(new_fav)
            db.commit()
    return JSONResponse({"status": "ok"})

@app.post("/api/favorites/remove")
async def favorites_remove(request: Request, user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    url = data.get("video_url", "")
    existing = db.exec(select(Favorite).where(Favorite.user_id == user.id, Favorite.video_url == url).limit(1)).first()
    if existing:
        db.delete(existing)
        db.commit()
    return JSONResponse({"status": "ok"})

# --- History ---
@app.get("/api/history-page", response_class=HTMLResponse)
async def history_page(request: Request, user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return HTMLResponse("Needs login")
    history = db.exec(select(SearchHistory).where(SearchHistory.user_id == user.id).order_by(SearchHistory.searched_at.desc()).limit(50)).all()
    ctx = get_auth_context(request, user)
    # Parse json previews
    for h in history: h.previews = json.loads(h.preview_thumbnails)
    ctx.update({"history": history})
    return templates.TemplateResponse("partials/history_page.html", ctx)

@app.delete("/api/history/clear")
async def history_clear(user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    history = db.exec(select(SearchHistory).where(SearchHistory.user_id == user.id)).all()
    for h in history: db.delete(h)
    db.commit()
    return JSONResponse({"status": "ok"})

# --- Radar & Spy (In-memory for simplicity) ---
_radar_keywords = []
_spy_accounts = []

@app.get("/api/radar-page", response_class=HTMLResponse)
async def radar_page(request: Request, user: User = Depends(get_user_from_cookie)):
    ctx = get_auth_context(request, user)
    ctx.update({"keywords": _radar_keywords})
    return templates.TemplateResponse("partials/radar_page.html", ctx)

@app.post("/api/radar/add")
async def radar_add(request: Request, keyword: str = Form(...), user: User = Depends(get_user_from_cookie)):
    if user and keyword not in _radar_keywords: _radar_keywords.append(keyword.strip())
    return HTMLResponse("OK")

@app.post("/api/radar/remove")
async def radar_remove(request: Request, keyword: str = Form(...), user: User = Depends(get_user_from_cookie)):
    if user and keyword in _radar_keywords: _radar_keywords.remove(keyword)
    return HTMLResponse("OK")

@app.get("/api/radar/results", response_class=HTMLResponse)
async def radar_results(request: Request, keyword: str = "", sort_by: str = "views", user: User = Depends(get_user_from_cookie)):
    videos = await social_api.search_trends(keyword, "all", sort_by) if keyword else []
    ctx = get_auth_context(request, user)
    ctx.update({"videos": videos, "page": 1, "section": "radar", "query": keyword})
    return templates.TemplateResponse("partials/video_grid.html", ctx)

@app.get("/api/spy-page", response_class=HTMLResponse)
async def spy_page(request: Request, user: User = Depends(get_user_from_cookie)):
    ctx = get_auth_context(request, user)
    ctx.update({"accounts": _spy_accounts})
    return templates.TemplateResponse("partials/spy_page.html", ctx)

@app.post("/api/spy/add")
async def spy_add(request: Request, username: str = Form(...), user: User = Depends(get_user_from_cookie)):
    if user and username not in _spy_accounts: _spy_accounts.append(username.strip())
    return HTMLResponse("OK")

@app.post("/api/spy/remove")
async def spy_remove(request: Request, username: str = Form(...), user: User = Depends(get_user_from_cookie)):
    if user and username in _spy_accounts: _spy_accounts.remove(username)
    return HTMLResponse("OK")

@app.get("/api/spy/results", response_class=HTMLResponse)
async def spy_results(request: Request, username: str = "", sort_by: str = "views", user: User = Depends(get_user_from_cookie)):
    videos = await rapidapi_service.search_reels_by_keyword_async(username, 20, None, sort_by) if username else []
    ctx = get_auth_context(request, user)
    ctx.update({"videos": videos, "page": 1, "section": "spy", "query": username})
    return templates.TemplateResponse("partials/video_grid.html", ctx)

# --- Video Analysis ---
@app.get("/api/video-analysis-page", response_class=HTMLResponse)
async def video_analysis_page(request: Request, user: User = Depends(get_user_from_cookie)):
    return templates.TemplateResponse("partials/video_analysis_page.html", get_auth_context(request, user))

@app.post("/api/analyze", response_class=HTMLResponse)
async def analyze(request: Request, video_url: str = Form(""), video_id: str = Form(""), platform: str = Form("instagram"), user: User = Depends(get_user_from_cookie), db: Session = Depends(get_session)):
    if not user: return HTMLResponse("Needs login")
    auth.deduct_tokens(user, 10, db) # Analysis is expensive
    vid = video_url or video_id
    video_data = {"platform_id": vid, "platform": platform, "video_url": vid}
    analysis = await ai_agent.analyze_video(video_data)
    ctx = get_auth_context(request, user)
    ctx.update({"analysis": analysis, "video_id": vid})
    return templates.TemplateResponse("partials/analysis_result.html", ctx)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
