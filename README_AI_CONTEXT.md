# Nocta Trends Pro - AI Context & Architecture documentation

This document is intended for future AI assistants working on this repository to quickly understand the application's current state, architecture, and quirks.

## 🚀 Tech Stack
- **Backend:** Python + FastAPI + SQLModel (SQLite database `nocta.db`).
- **Frontend:** HTML Templates (Jinja2) + TailwindCSS (via CDN) + HTMX + Vanilla JavaScript.
- **APIs:** RapidAPI (Instagram Reels parsing), Gemini API (AI Profile Analysis & Video Analysis), Apify (Hashtag Scraper, currently not active in UI due to speed).

## 📁 Project Structure
- `main.py` - The FastAPI application entry point. Contains all API routes (`/api/search`, `/api/anomalous`, `/api/profile`, etc.) and Jinja templating logic.
- `core/` - Core infrastructure (Database engine, Models).
- `models/` - SQLModel database definitions (`User`, `Video`, `Favorite`, `AnalysisHistory`, `SearchHistory`).
- `services/` - Business logic wrappers:
  - `rapidapi_service.py` - Core scraping engine. Uses a seed-account strategy (defined in `HASHTAG_TO_ACCOUNTS`) to rapidly fetch 100+ reels from specific niches (design, motion, business, tech) and filter them in-memory to bypass slow deep-scraping.
  - `auth.py` - Cookie-based session authentication.
  - `ai_agent.py` - Wrapper for Google Gemini API for deep analysis.
  - `social_api.py` - Simple routing wrapper for RapidAPI calls.
  - `instagram_service.py` - Apify integration (too slow for real-time, kept as a fallback).
- `frontend/`
  - `templates/` - HTML structure. `index.html` is the SPA shell. 
  - `templates/partials/` - HTMX/Fetch injected components (`video_grid.html`, `search_view.html`, `admin_page.html`, etc.).
  - `static/css/style.css` - Custom styling (dark mode, glassmorphism, flexbox scrolling).

## 🐛 Recent Fixes & Critical Behaviors
1. **Scrolling & Layout:** The app uses a complex flex layout (`height: 100vh` on `body` and `.main-wrapper`, with `.content-area { min-height: 0; overflow-y: auto }`). This allows the sidebar to stay fixed while the main content scrolls. Infinite scrolling uses an `IntersectionObserver` targeting `.page-content`.
2. **Infinite Scroll Pagination:** The frontend Javascript (`index.html`) manages pagination (`currentPage`, `currentSearchPage`). The backend endpoints (`/api/search`, `/api/anomalous`) receive `page=N`. They fetch massive arrays (~100 items), cache them in `app_cache`, and physically *slice* the array (`videos[start_idx:end_idx]`) before rendering the `partials/video_grid.html` component.
3. **API Rate Limiting (429):** RapidAPI `instagram120` free tier is highly restrictive. Do not increase concurrent fetches in `rapidapi_service.py`. The `max_accounts` is intentionally kept low (2) in `_pick_accounts()` to avoid instant 429 errors.
4. **Search UI Duplication:** Pagination requests strictly return `partials/video_grid.html`. The initial load (page=1) returns `search_view.html` (which includes the grid).
5. **Admin User:** The user `admin@nocta.app` (pass: `admin123`) has `tokens: 999999`. The `deduct_tokens` function explicitly ignores token deduction for the "admin" role. Normal users lose 2 tokens per search and 10 per deep analysis.

## 🛠️ Known Issues / Future Work
- The RapidAPI Instagram reels endpoint does not return the `taken_at` timestamp reliably. `rapidapi_service.extract_timestamp_from_pk` decodes the 64-bit Instagram Media PK (ID) to reconstruct the creation date for the `7d`/`3d`/`1d` filters.
- Apify is more accurate for hashtag searching but way too slow for a synchronous web request. A potential feature is to use WebSockets or Polling for asynchronous deep-scraping tasks.
