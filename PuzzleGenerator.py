"""
Difficulty-targeted Sudoku puzzle generator (Hill Climbing + Simulated Annealing).

Works with the team's two solver files (keep all three in the same folder):
  * PropagationSolverInitial.py  - scores difficulty (guesses), checks uniqueness
  * BacktrackingSolverInitial.py - baseline solver, used to double-check results

How it works
------------
A puzzle is a full solved grid plus the SET OF CELLS that are shown as clues.
Search moves change which cells are clues:
    remove a clue | add a clue | swap (remove one clue, add one blank cell)
Every candidate must still have EXACTLY ONE solution (count_solutions == 1),
otherwise the move is rejected. The cost of a puzzle is how far its difficulty
score (guesses from the propagation solver) is from the requested band:
    cost = 0 if the score is inside the band, else distance to the band edge.
  * Hill climbing:        accepts a move only if cost does not get worse.
                          Restarts from a fresh puzzle when stuck.
  * Simulated annealing:  also accepts worse moves with probability
                          exp(-delta / T), T cooling geometrically.

Usage
-----
  python PuzzleGenerator.py                        # one puzzle per band, both methods
  python PuzzleGenerator.py --band hard --method sa
  python PuzzleGenerator.py --play medium          # play a generated puzzle
  python PuzzleGenerator.py --experiment 100       # Table 3 / Figure 4 data (100 per band)
  python PuzzleGenerator.py --calibrate 1000       # suggest band cutoffs from a random sample
"""

import argparse
import math
import random
import time

import PropagationSolverInitial as prop
import BacktrackingSolverInitial as base

# ----------------------------------------------------------------------------
# Difficulty bands (guesses made by the propagation solver).
# Replace these with the cutoffs from Jake's 1,000-puzzle sample if they differ.
# ----------------------------------------------------------------------------
EASY_MAX = 0       # easy:   0 guesses (solved by propagation alone)
MEDIUM_MAX = 10    # medium: 1 to 10 guesses, hard: 11 or more
BANDS = {
    "easy": (0, EASY_MAX),
    "medium": (EASY_MAX + 1, MEDIUM_MAX),
    "hard": (MEDIUM_MAX + 1, math.inf),
}

# Clue count the starting puzzle is thinned down to, per band (a starting point only;
# the search is free to add or remove clues afterwards).
START_CLUES = {"easy": 38, "medium": 30, "hard": 0}   # 0 = remove until minimal

ALL_CELLS = [(r, c) for r in range(9) for c in range(9)]


# ----------------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------------
def random_solution(rng):
    """A random completed grid: fill the 3 diagonal boxes randomly, let the solver finish."""
    board = [[0] * 9 for _ in range(9)]
    for k in range(3):
        digits = list(range(1, 10))
        rng.shuffle(digits)
        for i, d in enumerate(digits):
            board[3 * k + i // 3][3 * k + i % 3] = d
    prop.solve_sudoku(board)
    return board


def to_board(solution, clues):
    return [[solution[r][c] if (r, c) in clues else 0 for c in range(9)] for r in range(9)]


def is_unique(solution, clues):
    return prop.count_solutions(to_board(solution, clues)) == 1


def rate(solution, clues):
    """Difficulty score = guesses the propagation solver needs (0 = no search)."""
    board = to_board(solution, clues)
    prop.solve_sudoku(board)
    return prop.guesses


def band_of(score):
    for name, (lo, hi) in BANDS.items():
        if lo <= score <= hi:
            return name
    return "hard"


def cost(score, band):
    lo, hi = BANDS[band]
    if score < lo:
        return lo - score
    if score > hi:
        return score - hi
    return 0


def initial_puzzle(band, rng):
    """Random unique puzzle: remove clues from a full grid while it stays unique."""
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
    """Random move on the clue set. Returns a new clue set, or None if not unique."""
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
    """Accept moves that do not make the cost worse; restart when stuck."""
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
            if cand_cost <= current:                   # sideways moves allowed
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
    """Like hill climbing, but worse moves are accepted with probability exp(-delta/T).
    Temperature cools geometrically (T *= cooling); reheats if it bottoms out early."""
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
        if temp < t_end:                               # reheat
            temp = t_start
    return best


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def generate(band="medium", method="sa", seed=None, max_seconds=20):
    """Generate one puzzle. Returns a dict with the puzzle, its solution and stats.
    `in_band` is False if the time limit ran out before the target band was hit."""
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
    """Cross-check with the plain backtracking baseline (can be slow on hard puzzles)."""
    board = [row[:] for row in result["puzzle"]]
    return base.solve_sudoku(board) and board == result["solution"]


def print_board(board):
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
    """Score n random unique puzzles to see the guess distribution (for choosing cutoffs)."""
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
