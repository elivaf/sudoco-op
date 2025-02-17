import os
import random
import time
import threading
from copy import deepcopy
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

class Grid:
    def __init__(self):
        self.values = [[0] * 9 for _ in range(9)]
        self.filled = [[0] * 9 for _ in range(9)]
        self.last_reset_time = 0

    def is_safe(self, row, col, num):
        if num in self.values[row]:
            return False
        if num in [self.values[i][col] for i in range(9)]:
            return False
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if self.values[start_row + i][start_col + j] == num:
                    return False
        return True

    def fill(self):
        for row in range(9):
            for col in range(9):
                if self.values[row][col] == 0:
                    for num in random.sample(range(1, 10), 9):
                        if self.is_safe(row, col, num):
                            self.values[row][col] = num
                            if self.fill():
                                return True
                            self.values[row][col] = 0
                    return False
        return True

    def count_solutions(self):
        def solve(count, grid):
            for row in range(9):
                for col in range(9):
                    if grid.values[row][col] == 0:
                        for num in range(1, 10):
                            if grid.is_safe(row, col, num):
                                grid.values[row][col] = num
                                count = solve(count, deepcopy(grid))
                                if count > 1:
                                    return count
                                grid.values[row][col] = 0
                        return count
            return count + 1

        return solve(0, deepcopy(self))

    def generate_sudoku(self, difficulty=60):
        self.fill()
        self.filled = deepcopy(self.values)
        cells = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(cells)
        removed = 0
        for row, col in cells:
            backup = self.values[row][col]
            self.values[row][col] = 0
            if self.count_solutions() != 1:
                self.values[row][col] = backup
            else:
                removed += 1
            if removed >= difficulty:
                break

    def reset_if_needed(self):
        if time.time() - self.last_reset_time > 5:
            print("\n============= Answer =============")  # Лог в консоль сервера
            for row in self.filled:
                print(" ".join(str(num) for num in row))
            print("====================================\n")
            self.__init__()
            self.generate_sudoku(difficulty=60)
            self.last_reset_time = time.time()
            return True
        return False

sudoku_game = Grid()
sudoku_game.generate_sudoku(difficulty=60)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('get_board')
def handle_get_board():
    emit('send_board', {'board': sudoku_game.values})

@socketio.on('make_move')
def handle_make_move(data):
    row, col, num = data['row'], data['col'], data['num']
    if sudoku_game.values[row][col] == 0:
        if num != sudoku_game.filled[row][col]:  
            if sudoku_game.reset_if_needed():
                emit('send_board', {'board': sudoku_game.values}, broadcast=True)
        else:
            sudoku_game.values[row][col] = num
            emit('send_board', {'board': sudoku_game.values}, broadcast=True)
            if all(sudoku_game.values[r][c] == sudoku_game.filled[r][c] for r in range(9) for c in range(9)):
                if sudoku_game.reset_if_needed():
                    emit('send_board', {'board': sudoku_game.values}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
