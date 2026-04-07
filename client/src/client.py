"""
This module contains the main client loop
that runs on the Raspberry Pi Zero 2W
"""

"""

from src.hardware_services.speaker_service import PyAudioSpeakerService
from src.hardware_services.network_service import WebSocketService
from src.hardware_services.screen_service import ScreenService

from src.software_services.speech_detection_service import WebRtcService
"""
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from src.software_services.wakeword_service import OpenWakeWordService
from config import WAKEWORD_MODEL_PATH
from openwakeword.model import Model


def main():
    """This is the main pi loop"""
    microphone = PyAudioMicrophoneService()
    wakeword_model = Model(WAKEWORD_MODEL_PATH)
    wakeword = OpenWakeWordService(model=wakeword_model)
    """
    vad = WebRtcService()
    server = WebSocketService()
    speaker = PyAudioSpeakerService()
    """
    while True:
        # listen for input

        # if wakeword detected - openwakeword
        # listen for user input
        # if user spoke - webrtc vad
        # listen for full query
        # stream query to server
        # wait for response
        # play server response
        pass


main()
