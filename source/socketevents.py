from .extensions import socketio

@socketio.on("connect")
def test_connect():
    print("Client Connected")

@socketio.on("disconnect")
def test_disconnect():
    print("Client Disconnect")

@socketio.on("sendFrequencyURL")
def handleFrequencyURL(frequencyURL):
    print(f"Established Connection for client with {frequencyURL}")