"""
Sudoku puzzle generator (Hill Climbing + Simulated Annealing).

What this file does:
  You ask for an easy, medium or hard puzzle, and it builds one for you.

It needs the other two files from our team in the same folder:
  * PropagationSolverInitial.py  - counts guesses (our difficulty score)
                                   and checks a puzzle has only one answer
  * BacktrackingSolverInitial.py - the basic solver, used to double-check

The big idea:
  A puzzle is a finished grid plus a list of which cells we SHOW as clues.
  We keep changing which cells are clues until the puzzle is the
  difficulty we asked for. A change can be:
      - remove a clue
      - add a clue
      - swap a clue with a blank cell
  Every changed puzzle must still have exactly ONE solution, or we throw
  the change away.

  "Cost" = how far the puzzle's difficulty is from the band we want.
  Cost 0 means we hit the band. Lower cost is better.
    * Hill climbing:       keep a change if the cost is not worse.
                           If we get stuck, start over with a new puzzle.
    * Simulated annealing: same, but sometimes keep a WORSE change too.
                           Early on it does this a lot, later less and less
                           (like a hot metal cooling down).

How to run it:
  python PuzzleGenerator.py                        # one puzzle per band, both methods
  python PuzzleGenerator.py --band hard --method sa
  python PuzzleGenerator.py --play medium          # play a puzzle in the terminal
  python PuzzleGenerator.py --experiment 100       # numbers for Table 3 / Figure 4
  python PuzzleGenerator.py --calibrate 1000       # help pick band cutoffs
"""

import argparse
import math
import random
import time

import PropagationSolverInitial as prop
import BacktrackingSolverInitial as base

# ----------------------------------------------------------------------------
# Difficulty bands
# Difficulty = number of guesses the propagation solver makes.
# These cutoffs are shared with the rest of the team (from the 1,000-puzzle sample).
# ----------------------------------------------------------------------------
EASY_MAX = 16      # easy: 0 to 16 guesses
MEDIUM_MAX = 60    # medium: 17 to 60, hard: 61+
BANDS = {
    "easy": (0, EASY_MAX),
    "medium": (EASY_MAX + 1, MEDIUM_MAX),
    "hard": (MEDIUM_MAX + 1, math.inf),   # math.inf just means "no upper limit"
}

# How many clues the first puzzle is cut down to (just a starting point).
# The search can add or remove clues after that. 0 means "remove as many as possible".
START_CLUES = {"easy": 38, "medium": 30, "hard": 0}

# A list of all 81 cells as (row, column) pairs.
ALL_CELLS = [(r, c) for r in range(9) for c in range(9)]


# ----------------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------------
def random_solution(rng):
    """Make a random, fully filled-in Sudoku grid.
    We fill the three boxes on the diagonal with shuffled digits (they don't
    affect each other), then let the solver fill in the rest."""
    board = [[0] * 9 for _ in range(9)]
    for k in range(3):
        digits = list(range(1, 10))
        rng.shuffle(digits)
        for i, d in enumerate(digits):
            board[3 * k + i // 3][3 * k + i % 3] = d
    prop.solve_sudoku(board)
    return board


def to_board(solution, clues):
    """Turn a solved grid + a set of clue cells into a puzzle.
    Cells that are clues keep their digit, all other cells become 0 (blank)."""
    return [[solution[r][c] if (r, c) in clues else 0 for c in range(9)] for r in range(9)]


def is_unique(solution, clues):
    """Check the puzzle has exactly one solution (True) or not (False)."""
    return prop.count_solutions(to_board(solution, clues)) == 1


def rate(solution, clues):
    """Give the puzzle a difficulty score.
    The score is how many guesses the propagation solver needs.
    0 means it never had to guess, so it is easy."""
    board = to_board(solution, clues)
    prop.solve_sudoku(board)
    return prop.guesses


def band_of(score):
    """Turn a difficulty score into a band name: "easy", "medium" or "hard"."""
    for name, (lo, hi) in BANDS.items():
        if lo <= score <= hi:
            return name
    return "hard"


def cost(score, band):
    """How far a score is from the band we want.
    0 = inside the band. Otherwise, the number of guesses we are off by."""
    lo, hi = BANDS[band]
    if score < lo:
        return lo - score
    if score > hi:
        return score - hi
    return 0


def initial_puzzle(band, rng):
    """Make a starting puzzle for the search.
    Start with a full grid and remove clues one at a time in random order.
    A clue only gets removed if the puzzle still has exactly one solution."""
    solution = random_solution(rng)
    clues = set(ALL_CELLS)
    order = ALL_CELLS[:]
    rng.shuffle(order)
    for cell in order:
        if len(clues) <= START_CLUES[band]:
            break
        trial = clues - {cell}
        if is_unique(solution, trial):
            clues = trial
    return solution, clues


def neighbour(solution, clues, rng):
    """Make one small random change to the clues (remove, add or swap).
    Returns the new set of clues, or None if the change gave a puzzle that
    does not have exactly one solution."""
    blanks = [c for c in ALL_CELLS if c not in clues]
    roll = rng.random()
    new = set(clues)
    if roll < 0.2 and len(clues) > 17:                 # remove a clue
        new.remove(rng.choice(list(clues)))
    elif roll < 0.4 and blanks:                        # add a clue (always stays unique)
        new.add(rng.choice(blanks))
        return new
    elif blanks:                                       # swap a clue with a blank cell
        new.remove(rng.choice(list(clues)))
        new.add(rng.choice(blanks))
    return new if is_unique(solution, new) else None


# ----------------------------------------------------------------------------
# Hill climbing
# ----------------------------------------------------------------------------
def hill_climb(band, rng, max_seconds=20, patience=300):
    """Search for a puzzle in the wanted band using hill climbing.
    Keep a change if the puzzle gets closer to the band (or stays as close).
    If 300 changes in a row don't help, give up on this puzzle and start a
    new one. Stops when we hit the band or run out of time."""
    start = time.perf_counter()
    best = None
    while time.perf_counter() - start < max_seconds:
        solution, clues = initial_puzzle(band, rng)
        score = rate(solution, clues)
        current = cost(score, band)
        stuck = 0
        while current > 0 and stuck < patience:
            if time.perf_counter() - start >= max_seconds:
                break
            cand = neighbour(solution, clues, rng)
            if cand is None:
                stuck += 1
                continue
            cand_score = rate(solution, cand)
            cand_cost = cost(cand_score, band)
            if cand_cost < current:
                stuck = 0
            else:
                stuck += 1
            if cand_cost <= current:                   # same cost is okay too
                clues, score, current = cand, cand_score, cand_cost
        if best is None or current < best[3]:
            best = (solution, clues, score, current)
        if current == 0:
            break
    return best


# ----------------------------------------------------------------------------
# Simulated annealing
# ----------------------------------------------------------------------------
def simulated_annealing(band, rng, max_seconds=20, t_start=3.0, t_end=0.05, cooling=0.995):
    """Search for a puzzle in the wanted band using simulated annealing.
    Like hill climbing, but a worse change is sometimes kept anyway.
    The "temperature" starts high (accepts worse changes often) and slowly
    cools down (accepts them less). If it gets too cold, we heat it up again.
    Stops when we hit the band or run out of time."""
    start = time.perf_counter()
    solution, clues = initial_puzzle(band, rng)
    score = rate(solution, clues)
    current = cost(score, band)
    best = (solution, set(clues), score, current)
    temp = t_start
    while current > 0 and time.perf_counter() - start < max_seconds:
        cand = neighbour(solution, clues, rng)
        if cand is not None:
            cand_score = rate(solution, cand)
            cand_cost = cost(cand_score, band)
            delta = cand_cost - current
            if delta <= 0 or rng.random() < math.exp(-delta / temp):
                clues, score, current = cand, cand_score, cand_cost
                if current < best[3]:
                    best = (solution, set(clues), score, current)
        temp *= cooling
        if temp < t_end:                               # too cold, heat up again
            temp = t_start
    return best


# ----------------------------------------------------------------------------
# Main function other code should call
# ----------------------------------------------------------------------------
def generate(band="medium", method="sa", seed=None, max_seconds=20):
    """Make one puzzle. This is the main function to call.
    band is "easy", "medium" or "hard". method is "hc" or "sa".
    Returns a dictionary with the puzzle, its solution and some stats.
    "in_band" is False if time ran out before we hit the wanted band."""
    rng = random.Random(seed)
    t0 = time.perf_counter()
    search = hill_climb if method == "hc" else simulated_annealing
    solution, clues, score, final_cost = search(band, rng, max_seconds=max_seconds)
    puzzle = to_board(solution, clues)
    return {
        "puzzle": puzzle,
        "solution": solution,
        "clues": len(clues),
        "guesses": score,
        "band": band_of(score),
        "requested": band,
        "in_band": final_cost == 0,
        "unique": prop.count_solutions(puzzle) == 1,
        "seconds": time.perf_counter() - t0,
    }


def verify_with_baseline(result):
    """Double-check a puzzle with the basic backtracking solver.
    Returns True if it finds the same solution we stored.
    Can be slow on hard puzzles."""
    board = [row[:] for row in result["puzzle"]]
    return base.solve_sudoku(board) and board == result["solution"]


def print_board(board):
    """Print a grid in the terminal. Blank cells show as '.', with lines
    between the 3x3 boxes."""
    for r in range(9):
        if r and r % 3 == 0:
            print("------+-------+------")
        print(" ".join(
            ((str(board[r][c]) if board[r][c] else ".") + (" |" if c in (2, 5) else ""))
            for c in range(9)).replace("  ", " "))


# ----------------------------------------------------------------------------
# Experiment (Table 3 / Figure 4) and calibration
# ----------------------------------------------------------------------------
def experiment(n, seconds=20):
    """Make n puzzles per band for each method and print a results table.
    Shows the % of puzzles that landed in the band (and were unique)
    and the average time in seconds. This is the data for Table 3 / Figure 4."""
    print(f"{'Band':<8}{'HC in band %':>14}{'SA in band %':>14}{'HC time (s)':>13}{'SA time (s)':>13}")
    for band in BANDS:
        stats = {}
        for method in ("hc", "sa"):
            hits, total_time = 0, 0.0
            for i in range(n):
                res = generate(band, method, seed=1000 + i, max_seconds=seconds)
                hits += res["in_band"] and res["unique"]
                total_time += res["seconds"]
            stats[method] = (100 * hits / n, total_time / n)
        print(f"{band:<8}{stats['hc'][0]:>14.1f}{stats['sa'][0]:>14.1f}"
              f"{stats['hc'][1]:>13.2f}{stats['sa'][1]:>13.2f}")


def calibrate(n):
    """Score n random puzzles and print how many guesses they need.
    Use this to help choose the cutoffs between easy, medium and hard."""
    rng = random.Random(7)
    scores = []
    for _ in range(n):
        solution = random_solution(rng)
        clues = set(ALL_CELLS)
        order = ALL_CELLS[:]
        rng.shuffle(order)
        for cell in order[:rng.randint(40, 60)]:
            if is_unique(solution, clues - {cell}):
                clues.remove(cell)
        scores.append(rate(solution, clues))
    scores.sort()
    print(f"{n} puzzles; 33rd percentile = {scores[n // 3]}, 66th = {scores[2 * n // 3]}, max = {scores[-1]}")


# ----------------------------------------------------------------------------
# Tiny playable game
# ----------------------------------------------------------------------------
def play(band):
    """Play a generated puzzle in the terminal.
    Type 'row col digit' to fill a cell, 'hint' for a free answer,
    'solve' to see the solution, or 'quit' to stop."""
    print(f"Generating a {band} puzzle...")
    res = generate(band, "sa")
    board, given = res["puzzle"], [[v != 0 for v in row] for row in res["puzzle"]]
    print("Enter 'row col digit' (1-9), 'row col 0' to clear, 'hint', 'solve' or 'quit'.")
    while True:
        print_board(board)
        if board == res["solution"]:
            print("Solved! Nice work.")
            return
        cmd = input("> ").split()
        if cmd == ["quit"]:
            return
        if cmd == ["solve"]:
            print_board(res["solution"])
            return
        if cmd == ["hint"]:
            r, c = next((r, c) for r, c in ALL_CELLS if board[r][c] != res["solution"][r][c])
            board[r][c] = res["solution"][r][c]
            print(f"Row {r + 1}, col {c + 1} = {board[r][c]}")
            continue
        try:
            r, c, d = (int(x) for x in cmd)
            assert 1 <= r <= 9 and 1 <= c <= 9 and 0 <= d <= 9 and len(cmd) == 3
        except (ValueError, AssertionError):
            print("Try e.g. '3 4 7'.")
            continue
        if given[r - 1][c - 1]:
            print("That cell is a clue.")
        else:
            board[r - 1][c - 1] = d
            if d and d != res["solution"][r - 1][c - 1]:
                print("(That digit does not match the solution.)")


# ----------------------------------------------------------------------------
# Command-line part: reads what you typed after "python PuzzleGenerator.py"
# and calls the right function above.
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sudoku puzzle generator (HC / SA)")
    ap.add_argument("--band", choices=list(BANDS))
    ap.add_argument("--method", choices=["hc", "sa"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--seconds", type=float, default=20, help="time limit per puzzle")
    ap.add_argument("--play", choices=list(BANDS), help="play a generated puzzle")
    ap.add_argument("--experiment", type=int, metavar="N", help="N puzzles per band per method")
    ap.add_argument("--calibrate", type=int, metavar="N")
    ap.add_argument("--verify", action="store_true", help="also check with the baseline solver")
    args = ap.parse_args()

    if args.play:
        play(args.play)
    elif args.experiment:
        experiment(args.experiment, args.seconds)
    elif args.calibrate:
        calibrate(args.calibrate)
    else:
        for band in ([args.band] if args.band else BANDS):
            for method in ([args.method] if args.method else ["hc", "sa"]):
                res = generate(band, method, args.seed, args.seconds)
                print(f"\n=== requested {band} via {'hill climbing' if method == 'hc' else 'simulated annealing'} ===")
                print_board(res["puzzle"])
                line = (f"clues {res['clues']}  guesses {res['guesses']}  band {res['band']}  "
                        f"unique {'yes' if res['unique'] else 'no'}  in band {'yes' if res['in_band'] else 'no'}  "
                        f"time {res['seconds']:.2f}s")
                if args.verify:
                    line += f"  baseline agrees {'yes' if verify_with_baseline(res) else 'no'}"
                print(line)
