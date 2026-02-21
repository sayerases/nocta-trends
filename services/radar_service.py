from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.database import engine, get_session
from sqlmodel import Session, select
from models.database import Video, RadarKeyword, AnalysisReport
from services.social_api import SocialAPIWrapper
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

social_api = SocialAPIWrapper()
scheduler = AsyncIOScheduler()

async def monitor_keywords():
    """
    Background task to check Instagram keywords for anomalous growth.
    """
    with Session(engine) as session:
        keywords = session.exec(select(RadarKeyword).where(RadarKeyword.active == True)).all()
        
        for k in keywords:
            print(f"Radar: Scanning Instagram for '{k.keyword}'...")
            results = await social_api.search_trends(k.keyword)
            
            for r in results:
                # Logic to detect anomalous growth (e.g., Views > 500k)
                if r['views'] > 100000:
                    # Check if already in DB
                    existing = session.exec(select(Video).where(Video.platform_id == r['platform_id'])).first()
                    if not existing:
                        video = Video(**r)
                        session.add(video)
                        print(f"Radar: Found anomalous Reel: {r['platform_id']}")
        
        session.commit()

def start_radar_scheduler():
    if not scheduler.running:
        scheduler.add_job(monitor_keywords, 'interval', minutes=30)
        scheduler.start()
        print("Radar Scheduler Started (30min interval)")
