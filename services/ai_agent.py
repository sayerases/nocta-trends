import os
import json
import google.generativeai as genai
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AIAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Using 1.5 Pro for depth
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.model = None

    async def analyze_video(self, video_data: Dict[str, Any], extra_meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze an Instagram Reel using Gemini 1.5 Pro.
        """
        if not self.model or self.api_key == "mocked_gemini_api_key":
            return self._get_mock_analysis()

        # Build a robust prompt for 1.5 Pro
        metadata_str = json.dumps({**video_data, **(extra_meta or {})}, indent=2)
        
        prompt = f"""
        Role: Expert Social Media Strategist and Video Editor.
        Task: Perform a deep architectural breakdown of this Instagram Reel metadata.
        
        Metadata:
        {metadata_str}
        
        Instructions:
        Extract the core 'winning formula' of this video. Return a valid JSON object with EXACTLY these keys:
        1. visual_hook: Focus on the first 3 seconds. What visual or text element grabs attention immediately?
        2. summary: The core value proposition and essence of the content.
        3. editing_techniques: List specific montage tricks (speed ramps, micro-cuts, text overlays, audio syncing).
        4. script_idea: A ready-to-shoot script based on this formula.
        
        Format: Return ONLY the raw JSON object.
        """

        try:
            # Note: For real multimodal, we could pass the video file here
            # But for the MVP/Specified flow, we analyze metadata/descriptions
            response = self.model.generate_content(prompt)
            
            text = response.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
            
            return self._get_mock_analysis()
        except Exception as e:
            print(f"Gemini 1.5 Pro Error: {e}")
            return self._get_mock_analysis()

    def _get_mock_analysis(self) -> Dict[str, Any]:
        return {
            "visual_hook": "Dynamic split-screen comparison showing 'Reality vs Expectation' with a bold text overlay.",
            "summary": "High-ticket lifestyle aspirational content emphasizing aesthetic consistency and status hooks.",
            "editing_techniques": [
                "Micro-cuts every 0.8 seconds to match high-tempo audio",
                "Subtle color grading (teal & orange preset)",
                "Floating text overlays in the 'center focus' zone",
                "Speed ramping during scene transitions"
            ],
            "script_idea": "HOOK: 'The truth about [Niche] they aren't telling you...' \nBODY: Montage of 3 aesthetic shots. Text overlay: 'It only takes 4 hours/day.' \nCTA: 'Read the caption for the roadmap.'"
        }
