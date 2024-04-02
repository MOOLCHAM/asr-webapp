from flask import request
from ..utils.transcribe_given_audio_file import Transcribe_ATC
import numpy as np
import requests
import subprocess
import nemo.collections.asr as nemo_asr
from ..socketevents import socketio

activeTranscriptionSessions = {}
activeTranscriptionBuffers = {}

# this object does the transcription
#transcribe = Transcribe_ATC()

transcribe = nemo_asr.models.EncDecCTCModel.from_pretrained(model_name="QuartzNet15x5Base-En")


def fetch_stream(stream_url):
    # Read stream, save to wav
    # stream_url = "http://d.liveatc.net/kdab_del_gnd"
    
    return requests.get(stream_url, stream=True)


def get_transcription_array(filename):
    # Convert mp3 to wav
    subprocess.call(["ffmpeg", "-y", "-i", filename, "stream.wav"])

    # TODO address error: Estimating duration from bitrate, this may be inaccurate
    # [src/libmpg123/layer3.c:INT123_do_layer3():1773] error: part2_3_length (1088) too large for available bit count (712)

    # Pass file to model, get transcription result
    #return transcribe.transcribe_audio("stream.wav")
    return transcribe.transcribe(["stream.wav"])


def audio_fetch_and_transcribe(stream_url, sessionID):
    activeTranscriptionSessions[sessionID] = True
    activeTranscriptionBuffers[sessionID] = []

    r = fetch_stream(stream_url)
    filename = "stream.mp3"

    for block in r.iter_content(6144):
        if activeTranscriptionSessions[sessionID] == True:
            # Write 3 seconds of streamed data to the file
            with open(filename, "wb") as f:
                f.write(block)
            f.close()

            # Transcribe
            transcription = get_transcription_array(filename)[0]

            if transcription:
                activeTranscriptionBuffers[sessionID] += transcription.split(" ")  # Add new words to array
                activeTranscriptionBuffers[sessionID] = activeTranscriptionBuffers[sessionID][-20:]  # Truncate the array to only the last 20

            # Format the message from the array and return to the appropriate session ID
            transcriptionMessage = " ".join(activeTranscriptionBuffers[sessionID])
            socketio.emit("latestTranscription", transcriptionMessage, to=sessionID)

        else:
            r.close()
            del activeTranscriptionSessions[request.sid]
            del activeTranscriptionBuffers[request.sid]
            break

@socketio.on("endTranscription")
def endTranscription():
    activeTranscriptionSessions[request.sid] = False

