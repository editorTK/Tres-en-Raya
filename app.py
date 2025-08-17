import os
import random
from uuid import uuid4
from collections import deque
import time
from threading import Timer

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

from game import Game

# --- Flask & SocketIO setup ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "devsecret")
# eventlet or gevent are supported; eventlet is easiest locally.
socketio = SocketIO(app, cors_allowed_origins="*")

# --- In-memory matchmaking & games ---
waiting_queue = deque()              # SIDs waiting for a match
sid_to_room = {}                     # sid -> room id
games = {}                           # room id -> Game instance
sid_to_symbol = {}                   # sid -> 'X' or 'O'

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return {"status": "ok"}

# ---------------- Socket.IO events ----------------
@socketio.on("connect")
def on_connect():
    emit("connected", {"ok": True})

@socketio.on("find_match")
def on_find_match():
    sid = request.sid

    # Remove duplicate entries of this sid in waiting queue, if any
    try:
        while True:
            waiting_queue.remove(sid)
    except ValueError:
        pass

    if waiting_queue:
        # Pair with the first waiting player
        opponent_sid = waiting_queue.popleft()
        room = str(uuid4())[:8]

        # Randomly assign symbols
        symbols = ["X", "O"]
        random.shuffle(symbols)
        players = {symbols[0]: opponent_sid, symbols[1]: sid}
        sid_to_symbol[opponent_sid] = symbols[0]
        sid_to_symbol[sid] = symbols[1]

        # Create new game
        game = Game()
        game.players = players
        games[room] = game

        # Join both players to the room and map sids
        join_room(room, sid=opponent_sid)
        join_room(room, sid=sid)
        sid_to_room[opponent_sid] = room
        sid_to_room[sid] = room

        # Notify both players
        emit("match_found", {
            "room": room,
            "symbol": sid_to_symbol[opponent_sid],
            "first_turn": game.turn,
            "board": game.board
        }, to=opponent_sid)

        emit("match_found", {
            "room": room,
            "symbol": sid_to_symbol[sid],
            "first_turn": game.turn,
            "board": game.board
        }, to=sid)
    else:
        # Put this player in the queue
        waiting_queue.append(sid)
        emit("searching", {"message": "Buscando contrincante..."})

@socketio.on("cancel_search")
def on_cancel_search():
    sid = request.sid
    try:
        while True:
            waiting_queue.remove(sid)
    except ValueError:
        pass
    emit("search_canceled", {"ok": True})

@socketio.on("make_move")
def on_make_move(data):
    sid = request.sid
    room = sid_to_room.get(sid)
    if not room:
        emit("error", {"message": "No estás en una partida."})
        return

    game = games.get(room)
    if not game:
        emit("error", {"message": "Partida inexistente."})
        return

    symbol = sid_to_symbol.get(sid)
    if symbol not in ("X", "O"):
        emit("error", {"message": "Símbolo desconocido."})
        return

    try:
        pos = int(data.get("position"))
    except (TypeError, ValueError):
        emit("move_rejected", {"reason": "Posición inválida."})
        return

    ok, reason = game.play(symbol, pos)
    if not ok:
        emit("move_rejected", {"reason": reason})
        return

    # Broadcast board update
    socketio.emit("game_update", {
        "board": game.board,
        "turn": game.turn
    }, to=room)
    
    if game.over:
    	schedule_rematch(game, delay=5)

    # If game ended, notify both
    if game.winner or game.draw:
        socketio.emit("game_over", {
            "winner": game.winner,  # 'X' or 'O' or None
            "draw": game.draw
        }, to=room)

@socketio.on("play_again")
def on_play_again():
    """Leave current room (if any) and re-enter matchmaking queue."""
    sid = request.sid
    _leave_current_game(sid)
    # Immediately search again
    on_find_match()

@socketio.on("leave_game")
def on_leave_game():
    sid = request.sid
    _leave_current_game(sid)
    emit("left_game", {"ok": True})

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    # Remove from waiting queue if present
    try:
        while True:
            waiting_queue.remove(sid)
    except ValueError:
        pass

    room = sid_to_room.get(sid)
    if room and room in games:
        # Inform opponent that this player left
        game = games[room]
        opponent_sid = None
        for sym, player_sid in game.players.items():
            if player_sid != sid:
                opponent_sid = player_sid
                break

        if opponent_sid:
            emit("opponent_left", {}, to=opponent_sid)

        # Cleanup
        _cleanup_room(room)

# ---------------- Helpers ----------------
def _cleanup_room(room):
    game = games.pop(room, None)
    if not game:
        return
    for sym, player_sid in game.players.items():
        sid_to_room.pop(player_sid, None)
        sid_to_symbol.pop(player_sid, None)

def _leave_current_game(leaver_sid):
    room = sid_to_room.get(leaver_sid)
    if not room:
        return
    game = games.get(room)
    opponent_sid = None
    if game:
        for sym, player_sid in game.players.items():
            if player_sid != leaver_sid:
                opponent_sid = player_sid
                break
    # Notify opponent
    if opponent_sid:
        socketio.emit("opponent_left", {}, to=opponent_sid)
    # Cleanup
    _cleanup_room(room)


def schedule_rematch(game, delay=5):
    def start_new():
        # reset game state
        game.board = [""] * 9
        game.turn = "X"
        game.over = False
        game.winner = None
        # notificar a ambos
        socketio.emit("rematch_started", game.public_state(), room=game.room_id)
    Timer(delay, start_new).start()

if __name__ == "__main__":
    # Use eventlet for WebSocket support in development.
    # Install with: pip install eventlet
    # Then run: python app.py
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))