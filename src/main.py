import schedule
import time
import yaml
import os
import sys
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load .env explicitly from project root
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

from youtube_client import YouTubeClient
from x_client import XClient
from db_manager import DatabaseManager

def load_config(path="config/config.yaml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Config file not found at {path}")
        return None

def format_number(num):
    """
    Format number in Japanese style for better impact.
    Examples:
        100000000 -> "1億"
        50000000 -> "5000万"
        1000000 -> "100万"
        500000 -> "50万"
        10000 -> "1万"
        1234 -> "1,234"
    """
    if num >= 100000000:  # 1億以上
        oku = num // 100000000
        remainder = num % 100000000
        if remainder == 0:
            return f"{oku}億"
        elif remainder >= 10000000:  # 1000万以上の端数
            man = remainder // 10000
            return f"{oku}億{man}万"
        else:
            return f"{oku}億"
    elif num >= 10000:  # 1万以上
        man = num // 10000
        return f"{man}万"
    else:
        return "{:,}".format(num)

def create_message(template_or_list, data):
    """
    Create a message by filling data into the template.
    If a list of templates is provided, select one randomly.
    """
    if isinstance(template_or_list, list):
        template = random.choice(template_or_list)
    else:
        template = template_or_list
        
    msg = template
    for key, value in data.items():
        msg = msg.replace("{" + key + "}", str(value))
    return msg



def get_milestone_step(view_count, milestones_config):
    """
    Determine the appropriate step (increment) based on current view count and rules.
    """
    rules = milestones_config.get('dynamic_rules', [])
    # If no dynamic rules, fallback to static 'step'
    if not rules:
        return milestones_config.get('step', 1000000)
    
    # Check rules (assuming they are sorted desc or we just find first match > threshold)
    # The config has them listed. We should iterate.
    for rule in rules:
        if view_count >= rule['threshold']:
            return rule['step']
    
    return milestones_config.get('step', 1000000)

def check_and_post(full_scan=False, init_mode=False):
    """
    Main function to check YouTube videos and post to X when milestones are reached.
    
    Args:
        full_scan: If True, scan all videos (not just recent 50)
        init_mode: If True, skip posting and just update DB with current milestones
                   (for initial setup - no posts, no limit, just record current state)
    """
    # Load configuration
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "config.yaml")
    config = load_config(config_path)
    
    if not config:
        print("Failed to load config. Exiting.")
        return
    
    # In init mode, disable post limit and skip actual posting
    if init_mode:
        max_posts = float('inf')  # No limit
        print("="*60)
        print("🚀 INIT MODE: Recording current milestone state to DB")
        print("   (No posts will be made, just updating database)")
        print("="*60)
    else:
        max_posts = config.get('system', {}).get('max_posts_per_run', 3)
    post_count = 0  # Track number of posts made
    
    # Initialize YouTube client
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    if not youtube_api_key:
        print("YOUTUBE_API_KEY not found in environment. Exiting.")
        return
    
    yt_client = YouTubeClient(youtube_api_key)
    
    # Initialize Database
    db_path = os.path.join(base_dir, "db", "mv_data.db")
    db = DatabaseManager(db_path)
    
    # Process each target
    for target in config.get('targets', []):
        artist_name = target['artist_name']
        account_id = target.get('account_id', 'DEFAULT')
        channel_id = target['channel_id']
        hashtags = " ".join(target.get('hashtags', []))
        title_keywords = target.get('title_keywords', [])
        exclude_keywords = target.get('exclude_keywords', [])  # 除外キーワード
        
        # Custom variables for templates
        custom_vars = target.get('custom_vars', {})
        custom_vars.setdefault('fan_name', 'ファン')
        custom_vars.setdefault('oshi_mark', '✨')
        custom_vars.setdefault('cheer_msg', f"{artist_name}最高！")
        
        print(f"\n{'='*60}")
        print(f"Processing: {artist_name} (Account: {account_id})")
        print(f"{'='*60}")
        
        # Initialize X client for this account (if credentials exist)
        x_client = None
        consumer_key = os.getenv(f"{account_id}_TWITTER_CONSUMER_KEY")
        consumer_secret = os.getenv(f"{account_id}_TWITTER_CONSUMER_SECRET")
        access_token = os.getenv(f"{account_id}_TWITTER_ACCESS_TOKEN")
        access_token_secret = os.getenv(f"{account_id}_TWITTER_ACCESS_TOKEN_SECRET")
        
        if all([consumer_key, consumer_secret, access_token, access_token_secret]):
            x_client = XClient(consumer_key, consumer_secret, access_token, access_token_secret)
            print("X client initialized successfully.")
        else:
            print("X credentials not found. Running in simulation mode.")
        
        # Fetch videos from channel
        videos = yt_client.get_channel_videos(channel_id, limit=50, full_scan=full_scan)
        print(f"Fetched {len(videos)} videos from channel.")
        
        videos_processed = 0
        top_video_info = None
        
        for video in videos:
            vid = video['id']
            title = video['title']
            view_count = video.get('view_count', 0)
            duration_seconds = video.get('duration_seconds', 0)
            video_url = f"https://www.youtube.com/watch?v={vid}"
            
            # Filter by title keywords if specified
            if title_keywords:
                if not any(kw.lower() in title.lower() for kw in title_keywords):
                    continue
            
            # Exclude videos matching exclude_keywords (e.g. 鑑賞会)
            if exclude_keywords:
                if any(kw.lower() in title.lower() for kw in exclude_keywords):
                    continue
            
            # Filter out shorts (less than 60 seconds typically)
            if duration_seconds < 60:
                continue
            
            videos_processed += 1
            
            # Update database
            db.update_video_stats(vid, title, artist_name, view_count)
            
            # Milestones logic
            milestone_step = get_milestone_step(view_count, target['milestones'])
            current_views = view_count
            
            # Debug info for top video
            if not top_video_info or current_views > top_video_info['views']:
                top_video_info = {'title': title, 'views': current_views}
            
            # --- Check Achievement (e.g. passed 1M, 2M...) ---
            # Calculation logic needs care.
            # Example: 105M views. Rules: >100M step 100M.
            # We want to know if it passed 100M recently.
            # achieved = (105M // 100M) * 100M = 100M.
            
            # Edge case: Transitioning rules?
            # If 9.9M -> step 1M. Next target 10M.
            # If 10.1M -> step 10M. Achieved 10M.
            # It works naturally.
            
            achieved_milestone = (current_views // milestone_step) * milestone_step
            
            if achieved_milestone >= target['milestones']['initial_target']:
                # Check if we already posted about this milestone
                if not db.check_history(vid, 'achieved', achieved_milestone):
                    # Check post limit
                    if post_count >= max_posts:
                        print(f"[SKIPPED] Post limit reached ({max_posts}). Skipping: {title}")
                    else:
                        # In init mode, just record to DB silently
                        if init_mode:
                            db.add_history(vid, 'achieved', achieved_milestone)
                            post_count += 1
                        else:
                            # Next goal calc
                            next_goal_val = achieved_milestone + milestone_step
                            
                            # Prepare Data
                            data = {
                                "artist_name": artist_name,
                                "video_title": title,
                                "views": format_number(achieved_milestone),
                                "next_goal": format_number(next_goal_val),
                                "video_url": video_url,
                                "hashtags": hashtags,
                                **custom_vars
                            }
                            msg = create_message(config['templates']['achieved'], data)
                            
                            print(f"\n[POST REQUEST] !!! ACHIEVEMENT UNLOCKED !!!")
                            print(f"Video: {title} passed {format_number(achieved_milestone)} views")
                            print("---------------------------------------------------")
                            print(msg)
                            print("---------------------------------------------------")
                            
                            if x_client:
                                success = x_client.post_tweet(msg)
                                if success:
                                    db.add_history(vid, 'achieved', achieved_milestone)
                                    post_count += 1
                            else:
                                db.add_history(vid, 'achieved', achieved_milestone)
                                post_count += 1
                                print("(Simulated post saved to DB)")

            # --- Check Support (Approaching milestone) ---
            next_milestone = achieved_milestone + milestone_step
            remaining = next_milestone - current_views
            
            # Sort triggers by remaining ASC (check most urgent first: 10k before 100k)
            sorted_triggers = sorted(target['support_trigger'], key=lambda x: x['remaining'])
            
            for trigger in sorted_triggers:
                trigger_val = trigger['remaining']
                
                if 0 < remaining <= trigger_val:
                    action_type = f"support_{trigger_val}"
                    
                    if not db.check_history(vid, action_type, next_milestone):
                        # In init mode, just record to DB silently
                        if init_mode:
                            db.add_history(vid, action_type, next_milestone)
                            # Don't count support in post_count for init mode summary
                        else:
                            # Check post limit
                            if post_count >= max_posts:
                                print(f"[SKIPPED] Post limit reached ({max_posts}). Skipping support: {title}")
                                break
                            
                            data = {
                                "artist_name": artist_name,
                                "video_title": title,
                                "target_views": format_number(next_milestone),
                                "current_views": format_number(current_views),
                                "remaining": format_number(remaining),
                                "video_url": video_url,
                                "hashtags": hashtags,
                                **custom_vars
                            }
                            msg = create_message(config['templates']['support'], data)
                            
                            print(f"\n[POST REQUEST] !!! SUPPORT NEEDED ({trigger_val}) !!!")
                            print(f"Video: {title} is attached to {format_number(next_milestone)}")
                            print("---------------------------------------------------")
                            print(msg)
                            print("---------------------------------------------------")
                            
                            if x_client:
                                success = x_client.post_tweet(msg)
                                if success:
                                    db.add_history(vid, action_type, next_milestone)
                                    post_count += 1
                            else:
                                db.add_history(vid, action_type, next_milestone)
                                post_count += 1
                                print("(Simulated post saved to DB)")
                        
                        break 
        
        if init_mode:
            print(f"✅ Recorded {post_count} milestone achievements to DB for {artist_name}")
        else:
            print(f"Processed {videos_processed} relevant videos (Filtered from {len(videos)} fetch results).")
        
        # --- 2. Update Stats for ALL Existing Videos in DB for THIS target ---
        # Skip this in init mode (we already did a full scan)
        # This ensures we track old MVs even if they are not in the latest 50 uploads.
        if not full_scan and not init_mode:
            print(f"\nUpdating stats for tracked videos of {artist_name} in DB...")
            # Get all video IDs from DB for this artist
            conn = db._get_connection()
            tracked_videos = conn.execute(
                "SELECT video_id FROM videos WHERE artist = ?", (artist_name,)
            ).fetchall()
            conn.close()
            tracked_ids = [r[0] for r in tracked_videos]
            
            # Process in chunks of 50 (API limit)
            for i in range(0, len(tracked_ids), 50):
                chunk_ids = tracked_ids[i:i+50]
                if not chunk_ids:
                    continue
                    
                stats_request = yt_client.youtube.videos().list(
                    part='statistics,snippet,contentDetails',
                    id=','.join(chunk_ids)
                )
                stats_response = stats_request.execute()
                
                for item in stats_response.get('items', []):
                    vid = item['id']
                    title = item['snippet']['title']
                    view_count = int(item['statistics'].get('viewCount', 0))
                    
                    # Update DB
                    db.update_video_stats(vid, title, artist_name, view_count)

                    # Milestones logic
                    milestone_step = get_milestone_step(view_count, target['milestones'])
                    current_views = view_count
                    
                    achieved_milestone = (current_views // milestone_step) * milestone_step

                    if achieved_milestone >= target['milestones']['initial_target']:
                        if not db.check_history(vid, 'achieved', achieved_milestone):
                            # Check post limit
                            if post_count >= max_posts:
                                print(f"[SKIPPED] Post limit reached ({max_posts}). Skipping: {title}")
                            else:
                                # Next goal calc
                                next_goal_val = achieved_milestone + milestone_step
                                
                                data = {
                                    "artist_name": artist_name,
                                    "video_title": title,
                                    "views": format_number(achieved_milestone),
                                    "next_goal": format_number(next_goal_val),
                                    "video_url": f"https://www.youtube.com/watch?v={vid}",
                                    "hashtags": hashtags,
                                    **custom_vars
                                }
                                msg = create_message(config['templates']['achieved'], data)
                                print(f"\n[POST] Achievement: {title} ({format_number(achieved_milestone)})")
                                if x_client:
                                    if x_client.post_tweet(msg):
                                        db.add_history(vid, 'achieved', achieved_milestone)
                                        post_count += 1
                                else:
                                    db.add_history(vid, 'achieved', achieved_milestone)
                                    post_count += 1
                    
                    # Check Support
                    next_milestone = achieved_milestone + milestone_step
                    remaining = next_milestone - current_views
                    
                    # Sort triggers by remaining ASC (check most urgent first: 10k before 100k)
                    sorted_triggers = sorted(target['support_trigger'], key=lambda x: x['remaining'])
                    
                    for trigger in sorted_triggers:
                        trigger_val = trigger['remaining']
                        if 0 < remaining <= trigger_val:
                            action_type = f"support_{trigger_val}"
                            
                            if not db.check_history(vid, action_type, next_milestone):
                                # Check post limit
                                if post_count >= max_posts:
                                    print(f"[SKIPPED] Post limit reached ({max_posts}). Skipping support: {title}")
                                    break
                                
                                data = {
                                    "artist_name": artist_name,
                                    "video_title": title,
                                    "target_views": format_number(next_milestone),
                                    "current_views": format_number(current_views),
                                    "remaining": format_number(remaining),
                                    "video_url": f"https://www.youtube.com/watch?v={vid}",
                                    "hashtags": hashtags,
                                    **custom_vars
                                }
                                msg = create_message(config['templates']['support'], data)
                                print(f"\n[POST] Support ({trigger_val}): {title} (Rem: {remaining})")
                                if x_client:
                                    if x_client.post_tweet(msg):
                                        db.add_history(vid, action_type, next_milestone)
                                        post_count += 1
                                else:
                                    db.add_history(vid, action_type, next_milestone)
                                    post_count += 1
                            
                            break

    print("Check cycle complete.")

if __name__ == "__main__":
    # GitHub Actions Execution Mode
    # We rely on environment variables or arguments.
    # Default behavior: Update existing + check latest (full_scan=False)
    # If run with specific flag, do full scan.
    
    import argparse
    parser = argparse.ArgumentParser(description="Idol MV Bot - YouTube view count monitor and X poster")
    parser.add_argument("--full-scan", action="store_true", help="Perform full scan of channel")
    parser.add_argument("--init", action="store_true", 
                        help="Initialize DB with current milestone state (no posting, just record)")
    args = parser.parse_args()
    
    check_and_post(full_scan=args.full_scan or args.init, init_mode=args.init)

