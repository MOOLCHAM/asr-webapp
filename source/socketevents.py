from flask import request

from .extensions import socketio
from .blueprints.models import transcribe #, endTranscriptionProcess

@socketio.on("connect")
def test_connect():
    print("Client Connected")

#@socketio.on("disconnect")
#def test_disconnect():
#    print("Client Disconnect")

@socketio.on("sendFrequencyURL")
def handleFrequencyURL(frequencyURL):
    print(f"Established Connection for client with {frequencyURL}")
    transcribe(frequencyURL, request.sid)

#@socketio.on("endTranscription")
#def endTranscription():
#    endTranscriptionProcess(request.sid)
