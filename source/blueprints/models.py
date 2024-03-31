from multiprocessing import Process, Lock, Manager
from flask import Blueprint, make_response, request
import subprocess
import sys
from ..socketevents import socketio

# # from multiprocessing import Process, Queue
# from asr_project.models import PretrainedFineTunedJasper, Model
# from asr_project.utils import transcribe_audio_buffer

bp = Blueprint("models", __name__, url_prefix="/models")

isNVIDIAGPUEnabled = ""

#manager = Manager()
#transcriptionProcessSessions = manager.dict()

try:
    subprocess.check_output('nvidia-smi') # this command will check if NVIDIA GPU AND appropriate drivers are installed, may fail if appropriate drivers not installed
    print('NVIDIA GPU Detected, webapp should function as expected.')
    isNVIDIAGPUEnabled = True
except Exception: # command may result in several different errors depending on config
    print('NVIDIA GPU Not Found!\nNVIDIA NeMo ASR will not be able to run without NVIDIA GPU, this may result in webapp features such as transcription\n unable to be used or unexpected issues.')
    isNVIDIAGPUEnabled = False

if isNVIDIAGPUEnabled == True:
    from ..utils.transcribing import audio_fetch_and_transcribe
# def asr_model_thread():
#     model = PretrainedFineTunedJasper(checkpoint_path="models/jasper_finetuned.nemo")


# model_init_process = Process(target=asr_model_thread)
# model_init_process.start()

# @bp.route("/transcribe", methods=["POST"])
def transcribe(frequencyURL, sessionID):
    """
    Endpoint URI: /models/transcribe

    """
    #requestBody = request.get_data()
    print(f"1sessionID: {sessionID}")
    if isNVIDIAGPUEnabled == True:
        # THIS DOESN'T MAKE A NEW PROCESS, WHICH MEANS WHEN USER HITS BUTTON IT TERMIANTES APP
        # CURRENTLY HERE BECAUSE BREAKS WHEN IN NEW PROCESS
        audio_fetch_and_transcribe(frequencyURL, sessionID)
        
        #Process(target=audio_fetch_and_transcribe, args=(transcriptionProcessSessions, frequencyURL, sessionID)).start()

#def endTranscriptionProcess(sessionID):
#    print(f"sessionIDs: {transcriptionProcessSessions}")
#    print(f"sessionID: {sessionID}")
#    os.kill(transcriptionProcessSessions.get(sessionID), signal.SIGTERM)
#    del transcriptionProcessSessions[sessionID]
#     """
#     Endpoint URI: /models/transcribe

#     Expects a JSON object in the request body with the following:
#     * ``audio_url`` - (``String`` | ``str``) The URL/URI to the audio stream to be transcribed

#     For example:

#         {
#             "audio_url": "https://livetraffic2.near.aero/stream/KDAB_132875.mp3"
#         }
#     """
#     request_body = request.get_data()
#     print(request_body)
#     # response = requests.get(request_body["audio_url"])
#     return make_response("Service has not been implemented", 501)

