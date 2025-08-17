(() => {
  const socket = io();

  // Elements
  const lobby = document.getElementById("lobby");
  const game = document.getElementById("game");
  const statusEl = document.getElementById("status");
  const findBtn = document.getElementById("findBtn");
  const cancelBtn = document.getElementById("cancelBtn");
  const youAreEl = document.getElementById("youAre");
  const turnEl = document.getElementById("turn");
  const boardEl = document.getElementById("board");
  const cells = Array.from(document.querySelectorAll(".cell"));
  const playAgainBtn = document.getElementById("playAgainBtn");
  const leaveBtn = document.getElementById("leaveBtn");
  const gameMsg = document.getElementById("gameMsg");

  // Client state
  let symbol = null;   // 'X' or 'O'
  let room = null;
  let myTurn = false;

  // --- UI helpers ---
  function showLobby() {
    lobby.classList.remove("hidden");
    game.classList.add("hidden");
    statusEl.textContent = "Pulsa “Buscar partida” para emparejar.";
  }
  function showGame() {
    lobby.classList.add("hidden");
    game.classList.remove("hidden");
  }
  function setMsg(text, cls = "") {
    gameMsg.textContent = text || "";
    gameMsg.className = "game-msg " + (cls || "");
  }
  function updateBoard(board) {
    board.forEach((val, i) => {
      const btn = cells[i];
      btn.textContent = val || "";
      btn.classList.toggle("x", val === "X");
      btn.classList.toggle("o", val === "O");
      btn.disabled = !!val || !myTurn;
    });
  }
  function updateTurn(turn) {
    myTurn = (turn === symbol);
    turnEl.textContent = turn;
    // Re-enable only empty cells if it's my turn
    cells.forEach((btn) => {
      btn.disabled = !!btn.textContent || !myTurn;
    });
  }

  // --- Event listeners (UI) ---
  findBtn.addEventListener("click", () => {
    statusEl.textContent = "Buscando contrincante...";
    socket.emit("find_match");
  });

  cancelBtn.addEventListener("click", () => {
    socket.emit("cancel_search");
  });

  playAgainBtn.addEventListener("click", () => {
    setMsg("");
    symbol = null;
    room = null;
    myTurn = false;
    // Clear board
    cells.forEach((btn) => {
      btn.textContent = "";
      btn.classList.remove("x", "o");
      btn.disabled = true;
    });
    showLobby();
    socket.emit("play_again");
  });

  leaveBtn.addEventListener("click", () => {
    socket.emit("leave_game");
    showLobby();
  });

  cells.forEach((btn) => {
    btn.addEventListener("click", () => {
      const pos = parseInt(btn.dataset.pos, 10);
      if (myTurn) {
        socket.emit("make_move", { position: pos });
      }
    });
  });

  // --- Socket handlers ---
  socket.on("connected", () => {
    // Auto-find a match as a convenience (optional).
    // Comment the next line if you prefer manual click.
    // socket.emit("find_match");
  });

  socket.on("searching", () => {
    statusEl.textContent = "Buscando contrincante...";
  });

  socket.on("search_canceled", () => {
    statusEl.textContent = "Búsqueda cancelada.";
  });

  socket.on("match_found", (data) => {
    showGame();
    room = data.room;
    symbol = data.symbol;
    youAreEl.textContent = symbol;
    updateBoard(data.board || Array(9).fill(""));
    updateTurn(data.first_turn);
    setMsg("¡Partida encontrada! Eres " + symbol + ".");
  });

  socket.on("game_update", (data) => {
    updateBoard(data.board);
    updateTurn(data.turn);
    setMsg("");
  });

  socket.on("move_rejected", (data) => {
    setMsg(data.reason || "Movimiento inválido.", "danger");
  });

  socket.on("game_over", ({ winner, draw }) => {
    if (draw) {
      setMsg("Empate 🤝", "draw");
    } else if (winner) {
      if (winner === symbol) setMsg("¡Ganaste! 🎉", "win");
      else setMsg("Perdiste. 😔", "danger");
    }
    // Disable all cells at the end
    cells.forEach((btn) => (btn.disabled = true));
  });

  socket.on("opponent_left", () => {
    setMsg("Tu contrincante abandonó la partida.", "danger");
    // Disable interactions
    cells.forEach((btn) => (btn.disabled = true));
  });

  socket.on("error", (data) => {
    setMsg(data.message || "Error de conexión.", "danger");
  });
  
  socket.on("rematch_started", (pub) => {
  roomId = pub.roomId;
  board = pub.board;
  turn = pub.turn;
  status = "running";
  lastPublic = pub;
  setUI();
});

  // Initial UI
  showLobby();
  // Keep cells disabled until match
  cells.forEach((btn) => (btn.disabled = true));
})();