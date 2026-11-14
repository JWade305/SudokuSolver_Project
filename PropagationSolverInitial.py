import time

guesses = 0  # difficulty score of the last puzzle solved


def get_peers(row, col):
    """The 20 cells that share a row, column or box with (row, col)."""
    peers = set()
    for i in range(9):
        peers.add((row, i))
        peers.add((i, col))
    box_row, box_col = 3 * (row // 3), 3 * (col // 3)
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            peers.add((r, c))
    peers.discard((row, col))
    return peers


PEERS = {(r, c): get_peers(r, c) for r in range(9) for c in range(9)}


def propagate(domains, queue):
    """Forward checking + AC-3. `queue` holds cells that are down to one digit.
    Returns False if any cell runs out of digits."""
    while queue:
        cell = queue.pop()
        digit = next(iter(domains[cell]))
        for peer in PEERS[cell]:
            if digit in domains[peer]:
                domains[peer].remove(digit)
                if len(domains[peer]) == 0:
                    return False
                if len(domains[peer]) == 1:
                    queue.append(peer)
    return True


def make_domains(board):
    """Possible digits for every cell after propagating the clues.
    Returns None if the clues contradict each other."""
    domains = {}
    for r in range(9):
        for c in range(9):
            domains[(r, c)] = {board[r][c]} if board[r][c] else set(range(1, 10))
    clues = [cell for cell in domains if len(domains[cell]) == 1]
    if not propagate(domains, clues):
        return None
    return domains


def pick_cell(domains):
    """MRV: the open cell with the fewest digits left (None if all are filled)."""
    open_cells = [cell for cell in domains if len(domains[cell]) > 1]
    if not open_cells:
        return None
    return min(open_cells, key=lambda cell: len(domains[cell]))


def search(domains):
    """Backtracking with MRV and propagation. Returns solved domains or None."""
    global guesses
    cell = pick_cell(domains)
    if cell is None:
        return domains

    for digit in sorted(domains[cell]):
        guesses += 1
        trial = {c: set(d) for c, d in domains.items()}  # a copy, so undo is free
        trial[cell] = {digit}
        if propagate(trial, [cell]):
            result = search(trial)
            if result is not None:
                return result
    return None


def solve_sudoku(board):
    """Fill `board` in place, like the baseline. Returns True if solved."""
    global guesses
    guesses = 0
    domains = make_domains(board)
    if domains is None:
        return False
    result = search(domains)
    if result is None:
        return False
    for (r, c), digits in result.items():
        board[r][c] = digits.pop()
    return True


def count_solutions(board, limit=2):
    """Number of solutions, stopping at `limit` (so 0, 1 or 2 by default).
    Exactly 1 means the puzzle is unique. Does not change `board`."""
    domains = make_domains(board)
    if domains is None:
        return 0
    return count_from(domains, limit)


def count_from(domains, limit):
    cell = pick_cell(domains)
    if cell is None:
        return 1
    total = 0
    for digit in sorted(domains[cell]):
        trial = {c: set(d) for c, d in domains.items()}
        trial[cell] = {digit}
        if propagate(trial, [cell]):
            total += count_from(trial, limit - total)
            if total >= limit:
                break
    return total


if __name__ == "__main__":
    puzzle = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]

    unique = count_solutions(puzzle) == 1
    start = time.perf_counter()
    solved = solve_sudoku(puzzle)
    ms = (time.perf_counter() - start) * 1000

    if solved:
        print("Solved Sudoku Grid:")
        for r in puzzle:
            print(r)
        print(f"Guesses: {guesses}   Time: {ms:.2f} ms   Unique: {'yes' if unique else 'no'}")
    else:
        print("No solution exists.")
