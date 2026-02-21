import os
import instaloader
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("INSTA_USER")
pwd = os.getenv("INSTA_PASS")

print(f"Loaded User: {user}")

loader = instaloader.Instaloader()
try:
    try:
        loader.load_session_from_file(user)
        print("Loaded session from file")
    except FileNotFoundError:
        print("No session file found, logging in...")
        loader.login(user, pwd)
        loader.save_session_to_file()
        print("Login success, session saved")
    
    # Try fetching a few posts from a profile instead of a hashtag
    profile = instaloader.Profile.from_username(loader.context, "instagram")
    for i, post in enumerate(profile.get_posts()):
        print(f"Got profile post {i}: {post.shortcode}")
        if i >= 2: break
except Exception as e:
    print(f"Login or fetch failed: {e}")
