import subprocess
import psutil

# We store the process globally so we can kill it easily in the same session
music_process = None

def play_music(query: str):
    global music_process
    
    # 1. STOP any music currently playing first
    stop_music()
    
    # 2. Start the new song
    # We use 'mpv' because it's easy to find in the process list later
    url_cmd = f"yt-dlp --get-id --flat-playlist \"ytsearch1:{query} official audio\""
    video_id = subprocess.check_output(url_cmd, shell=True).decode().strip()
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Start mpv in the background
    music_process = subprocess.Popen(["mpv", "--no-video", "--volume=40", url])
    return f"Now playing {query}."

def stop_music():
    """
    Kills the music by looking for the 'mpv' process name.
    This works even if the global variable was lost.
    """
    global music_process
    
    # Method A: Try to kill the specific object we have
    if music_process:
        music_process.terminate()
        music_process = None
    """
    # Method B: The "Nuclear" option (looks for any mpv instance)
    # This ensures no 'ghost' music stays playing if the script crashed earlier
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'mpv' or proc.info['name'] == 'mpv.exe':
            proc.kill()
    """     
    return "Music stopped."