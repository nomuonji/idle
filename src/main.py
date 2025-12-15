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
    """Format number with commas (e.g. 1,000,000)."""
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

def check_and_post(full_scan=False):
    # ... (omitted setup lines) ...
    # (Inside Loop)
    
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
                    else:
                        db.add_history(vid, 'achieved', achieved_milestone)
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
                        else:
                            db.add_history(vid, action_type, next_milestone)
                            print("(Simulated post saved to DB)")
                        
                        break 
        
        print(f"Processed {videos_processed} relevant videos (Filtered from {len(videos)} fetch results).")
    # --- 2. Update Stats for ALL Existing Videos in DB ---
    # This ensures we track old MVs even if they are not in the latest 50 uploads.
    if not full_scan:
        print("\nUpdating stats for tracked videos in DB...")
        # Get all video IDs from DB
        tracked_videos = db._get_connection().execute("SELECT video_id FROM videos").fetchall()
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
                
                # We can re-verify duration/keywords here if needed, but assuming DB is clean.
                # Update DB
                db.update_video_stats(vid, title, artist_name, view_count)

                # Prepare base data
                custom_vars = target.get('custom_vars', {})
                # Defaults if missing to prevent error
                custom_vars.setdefault('fan_name', 'ファン')
                custom_vars.setdefault('oshi_mark', '✨')
                custom_vars.setdefault('cheer_msg', f"{artist_name}最高！")

                # Milestones logic
                milestone_step = get_milestone_step(view_count, target['milestones'])
                current_views = view_count
                
                achieved_milestone = (current_views // milestone_step) * milestone_step

                if achieved_milestone >= target['milestones']['initial_target']:
                    if not db.check_history(vid, 'achieved', achieved_milestone):
                         # Next goal calc
                         next_goal_val = achieved_milestone + milestone_step
                         
                         data = {
                            "artist_name": artist_name,
                            "video_title": title,
                            "views": format_number(achieved_milestone),
                            "next_goal": format_number(next_goal_val),
                            "video_url": f"https://www.youtube.com/watch?v={vid}",
                            "hashtags": hashtags,
                            **custom_vars # Merge custom variables
                        }
                         msg = create_message(config['templates']['achieved'], data)
                         print(f"\n[POST] Achievement: {title} ({format_number(achieved_milestone)})")
                         if x_client:
                             if x_client.post_tweet(msg):
                                 db.add_history(vid, 'achieved', achieved_milestone)
                         else:
                             db.add_history(vid, 'achieved', achieved_milestone)
                
                # Check Support
                next_milestone = achieved_milestone + milestone_step
                remaining = next_milestone - current_views
                
                # Sort triggers by remaining ASC (check most urgent first: 10k before 100k)
                sorted_triggers = sorted(target['support_trigger'], key=lambda x: x['remaining'])
                
                for trigger in sorted_triggers:
                    trigger_val = trigger['remaining']
                    if 0 < remaining <= trigger_val:
                        # Use a unique action type for each trigger level to allow multiple support tweets
                        # e.g. 'support_100000', 'support_10000'
                        action_type = f"support_{trigger_val}"
                        
                        if not db.check_history(vid, action_type, next_milestone):
                            data = {
                                "artist_name": artist_name,
                                "video_title": title,
                                "target_views": format_number(next_milestone),
                                "current_views": format_number(current_views),
                                "remaining": format_number(remaining),
                                "video_url": f"https://www.youtube.com/watch?v={vid}",
                                "hashtags": hashtags,
                                **custom_vars # Merge custom variables
                            }
                            msg = create_message(config['templates']['support'], data)
                            print(f"\n[POST] Support ({trigger_val}): {title} (Rem: {remaining})")
                            if x_client:
                                if x_client.post_tweet(msg):
                                    db.add_history(vid, action_type, next_milestone)
                            else:
                                db.add_history(vid, action_type, next_milestone)
                        
                        break

    print("Check cycle complete.")

if __name__ == "__main__":
    # GitHub Actions Execution Mode
    # We rely on environment variables or arguments.
    # Default behavior: Update existing + check latest (full_scan=False)
    # If run with specific flag, do full scan.
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-scan", action="store_true", help="Perform full scan of channel")
    args = parser.parse_args()
    
    check_and_post(full_scan=args.full_scan)

