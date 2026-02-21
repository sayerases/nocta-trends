import os
from dotenv import load_dotenv
from services.social_api import SocialAPIWrapper
from services.ai_agent import AIAgent

load_dotenv()

class ProfileService:
    def __init__(self):
        self.social_api = SocialAPIWrapper()
        self.ai_agent = AIAgent()

    async def generate_growth_report(self, username: str, platform: str) -> dict:
        """
        Fetch last N videos for a profile and generate a Gemini growth report.
        """
        # In a real app, we'd have a specific profile fetch endpoint
        # Here we simulate by searching for the username
        results = await self.social_api.search_trends(username)
        
        # Aggregate stats
        total_views = sum(v['views'] for v in results)
        avg_er = sum(v['engagement_rate'] for v in results) / len(results) if results else 0
        
        summary_data = {
            "username": username,
            "platform": platform,
            "total_videos_analyzed": len(results),
            "total_views": total_views,
            "avg_engagement_rate": round(avg_er, 2)
        }
        
        # Ask Gemini to analyze the pattern
        prompt = f"Analyze these stats for {username} on {platform}: {summary_data}. Identify the virality pattern and 3 growth tips."
        # For MVP we'll use a mock response if no key
        if not self.ai_agent.model:
            return {
                **summary_data,
                "virality_pattern": "Strong aesthetic consistency with high-energy hooks.",
                "growth_tips": [
                    "Double down on the 'How-To' format which got 2x engagement",
                    "Optimize captions for SEO keywords found in trending tags",
                    "Collaborate with creators in the 'Tech' niche"
                ]
            }
            
        # Real Gemini analysis would go here...
        analysis = await self.ai_agent.analyze_video(summary_data) # Reusing analysis logic
        return {**summary_data, "report": analysis}
