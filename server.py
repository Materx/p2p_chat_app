"""
MeowChat Server — PWA ready
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
import os

app = Flask(__name__, static_folder=".", template_folder=".")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "meowchat-secret")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

users = {}
rooms = {}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    response = send_from_directory(".", "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@app.route("/icon-192.png")
def icon192():
    return send_from_directory(".", "icon-192.png", mimetype="image/png")

@app.route("/icon-512.png")
def icon512():
    return send_from_directory(".", "icon-512.png", mimetype="image/png")

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
        emit("status", {"msg": "Waiting for your friend to join...", "type": "waiting"})
    elif peer_count == 2:
        emit("status", {"msg": "Your friend is here! Say hello 👋", "type": "connected"})
        emit("peer_joined", {"name": name}, room=room, skip_sid=sid)
    else:
        emit("status", {"msg": "Room is full (max 2 people).", "type": "error"})
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

@socketio.on("typing")
def on_typing(data):
    from flask import request
    sid = request.sid
    if sid not in users:
        return
    user = users[sid]
    room = user["room"]
    emit("typing", {"name": user["name"], "typing": data.get("typing", False)}, room=room, skip_sid=sid)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
