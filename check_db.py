import sqlite3

db_path = "db/mv_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Videos Table (Top 5 by update time) ---")
try:
    cursor.execute("SELECT video_id, title, view_count, last_updated FROM videos ORDER BY last_updated DESC LIMIT 5")
    rows = cursor.fetchall()
    if not rows:
        print("No videos found.")
    for row in rows:
        # Truncate title for display
        title = row[1]
        if len(title) > 30:
            title = title[:27] + "..."
        print(f"[{row[0]}] {title} : {row[2]:,} views (Updated: {row[3]})")
except Exception as e:
    print(e)

print("\n--- Post History Table ---")
try:
    cursor.execute("SELECT * FROM post_history ORDER BY posted_at DESC")
    rows = cursor.fetchall()
    if not rows:
        print("No history found.")
    for row in rows:
        print(row)
except Exception as e:
    print(e)

conn.close()
