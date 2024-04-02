from flask import Blueprint
import subprocess
from ..socketevents import socketio

# from asr_project.models import PretrainedFineTunedJasper, Model
# from asr_project.utils import transcribe_audio_buffer

bp = Blueprint("models", __name__, url_prefix="/models")

isNVIDIAGPUEnabled = ""

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

def transcribe(frequencyURL, sessionID):
    """
    Using the NVIDIA GPU Check, if true continue to the transcription

    * ``frequencyURL`` - (``String`` | ``str``) The URL/URI to the audio stream to be transcribed
    * ``sessionID`` - (``String`` | ``str``) The session ID passed in from the Flask-SocketIO event that called this function

    """
    print(f"1sessionID: {sessionID}")
    if isNVIDIAGPUEnabled == True:
        audio_fetch_and_transcribe(frequencyURL, sessionID)


