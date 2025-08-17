from typing import List, Tuple, Optional

WIN_COMBOS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6)              # diagonals
]

class Game:
    def __init__(self):
        self.board: List[str] = [""] * 9
        self.turn: str = "X"
        self.winner: Optional[str] = None
        self.draw: bool = False
        self.players = {}  # {'X': sid_x, 'O': sid_o}

    def play(self, symbol: str, pos: int) -> Tuple[bool, str]:
        if self.winner or self.draw:
            return False, "La partida ya terminó."
        if symbol != self.turn:
            return False, "No es tu turno."
        if pos < 0 or pos > 8:
            return False, "Posición fuera de rango."
        if self.board[pos] != "":
            return False, "Casilla ocupada."

        self.board[pos] = symbol
        if self._has_winner(symbol):
            self.winner = symbol
            return True, ""
        if all(cell != "" for cell in self.board):
            self.draw = True
            return True, ""

        self.turn = "O" if self.turn == "X" else "X"
        return True, ""

    def _has_winner(self, symbol: str) -> bool:
        for a, b, c in WIN_COMBOS:
            if self.board[a] == self.board[b] == self.board[c] == symbol:
                return True
        return False