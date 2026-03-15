import subprocess

def play_music(query: str):
    """
    Searches YouTube Music and plays the first result using mpv.
    No API keys, no OAuth, no .env file needed.
    """
    try:
        # 1. Search for the video ID using yt-dlp (Search only)
        # We use 'ytsearch1' to get just the first result
        search_cmd = [
            "yt-dlp",
            f"ytsearch1: {query} official audio",
            "--get-id",
            "--flat-playlist",
            "--quiet"
        ]
        
        video_id = subprocess.check_output(search_cmd).decode().strip()
        
        if not video_id:
            return f"Could not find anything for '{query}'"

        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Playing: {url}")

        # 2. Play the audio stream directly using mpv
        # --no-video makes it audio-only (saves bandwidth/CPU)
        subprocess.Popen(["mpv", "--no-video", url])
        
        return f"Now playing the best match for '{query}'"

    except Exception as e:
        return f"Error: {str(e)}"