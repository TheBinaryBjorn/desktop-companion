"""
This module contains the main client loop
that runs on the Raspberry Pi Zero 2W
"""

from openwakeword.model import Model
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from src.software_services.wakeword_service import OpenWakeWordService
from src.config import WAKEWORD_MODEL_PATH


def main():
    """This is the main pi loop"""
    microphone = PyAudioMicrophoneService()
    wakeword_model = Model(WAKEWORD_MODEL_PATH)
    wakeword = OpenWakeWordService(model=wakeword_model)
    while True:
        # listen for input
        pcm_bytes = microphone.read_pcm_bytes()
        # if wakeword detected - openwakeword
        if wakeword.detect_wakeword(pcm_bytes):
            print("Wakeword Detected.")
            # listen for user input
        # if user spoke - webrtc vad
        # listen for full query
        # stream query to server
        # wait for response
        # play server response


main()
