def solve_sudoku(board, stats=None):
    if stats is None:
        stats = {"attempts": 0, "backtracks": 0}
    empty = find_empty_cell(board)
    if not empty:
        return True
    row, col = empty

    for num in range(1, 10):
        if is_valid(board, num, (row, col)):
            board[row][col] = num
            stats["attempts"] += 1
            if solve_sudoku(board, stats):
                return True
            board[row][col] = 0
            stats["backtracks"] += 1
    return False

def find_empty_cell(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return (r, c)
    return None


def is_valid(board, num, pos):
    row, col = pos
    if num in board[row]:
        return False
    if num in [board[r][col] for r in range(9)]:
        return False
    box_x = col // 3
    box_y = row // 3

    for r in range(box_y * 3, box_y * 3 + 3):
        for c in range(box_x * 3, box_x * 3 + 3):
            if board[r][c] == num and (r, c) != pos:
                return False
    return True

def assess_difficulty(board):
    test_board = [row[:] for row in board]
    stats = {"attempts": 0, "backtracks": 0}
    if not solve_sudoku(test_board, stats):
        return "Unsolvable", stats
    backtracks = stats["backtracks"]
    if backtracks <= 10:
        difficulty = "Easy"
    elif backtracks <= 300:
        difficulty = "Medium"
    else:
        difficulty = "Hard"

    return difficulty, stats

if __name__ == "__main__":

    puzzle = [
        [0, 0, 3, 0, 2, 0, 6, 0, 0],
        [9, 0, 0, 3, 0, 5, 0, 0, 1],
        [0, 0, 1, 8, 0, 6, 4, 0, 0],
        [0, 0, 8, 1, 0, 2, 9, 0, 0],
        [7, 0, 0, 0, 0, 0, 0, 0, 8],
        [0, 0, 6, 7, 0, 8, 2, 0, 0],
        [0, 0, 2, 6, 0, 9, 5, 0, 0],
        [8, 0, 0, 2, 0, 3, 0, 0, 9],
        [0, 0, 5, 0, 1, 0, 3, 0, 0]
    ]

    difficulty, stats = assess_difficulty(puzzle)

    print("Difficulty:", difficulty)
    print("Attempts:", stats["attempts"])
    print("Backtracks:", stats["backtracks"])

    if solve_sudoku(puzzle):
        print("\nSolved Puzzle:")
        for r in puzzle:
            print(r)
    else:
        print("No solution.")