"""
P2P Chat Server — production ready
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import os

app = Flask(__name__, static_folder=".", template_folder=".")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "p2p-chat-secret")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

users = {}
rooms = {}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@socketio.on("connect")
def on_connect():
    pass

@socketio.on("disconnect")
def on_disconnect():
    from flask import request
    sid = request.sid
    if sid in users:
        user = users[sid]
        room = user.get("room")
        name = user.get("name", "Someone")
        if room and room in rooms:
            rooms[room] = [s for s in rooms[room] if s != sid]
            emit("peer_left", {"name": name}, room=room)
            if not rooms[room]:
                del rooms[room]
        del users[sid]

@socketio.on("join")
def on_join(data):
    from flask import request
    sid = request.sid
    name = data.get("name", "Anonymous")
    room = data.get("room", "lobby")

    users[sid] = {"name": name, "room": room}
    join_room(room)

    if room not in rooms:
        rooms[room] = []
    rooms[room].append(sid)

    peer_count = len(rooms[room])

    if peer_count == 1:
        emit("status", {"msg": "Waiting for someone to join this room…", "type": "waiting"})
    elif peer_count == 2:
        emit("status", {"msg": "Connected! You're chatting with your peer.", "type": "connected"})
        emit("peer_joined", {"name": name}, room=room, skip_sid=sid)
    else:
        emit("status", {"msg": "Room is full (max 2 peers).", "type": "error"})
        leave_room(room)
        rooms[room] = [s for s in rooms[room] if s != sid]
        del users[sid]

@socketio.on("message")
def on_message(data):
    from flask import request
    sid = request.sid
    if sid not in users:
        return
    user = users[sid]
    room = user["room"]
    name = user["name"]
    emit("message", {
        "name": name,
        "text": data.get("text", ""),
        "sid": sid
    }, room=room)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
