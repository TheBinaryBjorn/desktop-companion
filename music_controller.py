import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

# --- Configuration ---
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8888/callback"

scope = "user-modify-playback-state user-read-playback-state"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    open_browser=False # Set to False for headless Raspberry Pi use
))

def play_spotify(query: str):
    """
    Searches for a track and plays it on the active Spotify device.
    Returns a status message for the LLM.
    """
    try:
        # 1. Search for the track
        results = sp.search(q=query, limit=1, type='track')
        items = results.get('tracks', {}).get('items')
        
        if not items:
            return f"Could not find any songs matching '{query}'."

        track_uri = items[0]['uri']
        track_name = items[0]['name']
        artist_name = items[0]['artists'][0]['name']

        # 2. Start Playback
        # Note: A Spotify device must be 'active' (recently used) for this to work
        sp.start_playback(uris=[track_uri])
        
        return f"Now playing: {track_name} by {artist_name}"

    except Exception as e:
        if "No active device found" in str(e):
            return "Error: No active Spotify device found. Please open Spotify on one of your devices."
        return f"An error occurred: {str(e)}"