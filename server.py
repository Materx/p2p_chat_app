"""
MeowChat Server — full featured
"""
import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import os

app = Flask(__name__, static_folder=".", template_folder=".")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "meowchat-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet",
                    max_http_buffer_size=5 * 1024 * 1024)  # 5MB for images

users = {}
rooms = {}

@app.route("/")
def index(): return send_from_directory(".", "index.html")

@app.route("/manifest.json")
def manifest(): return send_from_directory(".", "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def sw():
    r = send_from_directory(".", "sw.js", mimetype="application/javascript")
    r.headers["Service-Worker-Allowed"] = "/"
    return r

@app.route("/icon-192.png")
def icon192(): return send_from_directory(".", "icon-192.png")

@app.route("/icon-512.png")
def icon512(): return send_from_directory(".", "icon-512.png")

@socketio.on("connect")
def on_connect(): pass

@socketio.on("disconnect")
def on_disconnect():
    from flask import request
    sid = request.sid
    if sid in users:
        user = users.pop(sid)
        room = user.get("room")
        if room and room in rooms:
            rooms[room] = [s for s in rooms[room] if s != sid]
            emit("peer_left", {"name": user.get("name", "Someone")}, room=room)
            if not rooms[room]:
                del rooms[room]

@socketio.on("join")
def on_join(data):
    from flask import request
    sid = request.sid
    name = data.get("name", "Anonymous")
    room = data.get("room", "lobby")
    users[sid] = {"name": name, "room": room}
    join_room(room)
    if room not in rooms: rooms[room] = []
    rooms[room].append(sid)
    count = len(rooms[room])
    if count == 1:
        emit("status", {"msg": "Waiting for your friend to join...", "type": "waiting"})
    elif count == 2:
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
    if sid not in users: return
    user = users[sid]
    emit("message", {
        "name": user["name"],
        "text": data.get("text", ""),
        "type": data.get("type", "text"),
        "sid": sid,
        "msgId": data.get("msgId", ""),
        "replyTo": data.get("replyTo")
    }, room=user["room"])

@socketio.on("reaction")
def on_reaction(data):
    from flask import request
    sid = request.sid
    if sid not in users: return
    user = users[sid]
    emit("reaction", {
        "msgId": data.get("msgId"),
        "emoji": data.get("emoji"),
        "name": user["name"]
    }, room=user["room"])

@socketio.on("typing")
def on_typing(data):
    from flask import request
    sid = request.sid
    if sid not in users: return
    user = users[sid]
    emit("typing", {"name": user["name"], "typing": data.get("typing", False)},
         room=user["room"], skip_sid=sid)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
