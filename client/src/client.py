"""
This module contains the main client loop
that runs on the Raspberry Pi Zero 2W
"""

from src.hardware_services import (
    microphone_service,
    network_service,
    screen_service,
    speaker_service,
)


def main():
    """This is the main pi loop"""
    microphone = PyAudioMicrophoneService()
    wakeword = OpenWakeWordService()
    vad = WebRtcService()
    server = WebSocketService()
    speaker = PyAudioSpeakerService()
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
