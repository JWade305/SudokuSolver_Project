Sudoku Bactracking Solver 

A python program that solves a 9 by 9 puzzle using backtracking and rates the difficulty based on the number of search nodes. 

The only requirements are python 3

Usage:
run python backtrackerwithdiff.py in command line.	

A sample puzzle is held in the puzzle at the end of the file.

example output:
Difficulty: Medium
Attempts: 200
Backtracks: 151

Solved Puzzle:
[4, 8, 3, 9, 2, 1, 6, 5, 7]
[9, 6, 7, 3, 4, 5, 8, 2, 1]
[2, 5, 1, 8, 7, 6, 4, 9, 3]
[5, 4, 8, 1, 3, 2, 9, 7, 6]
[7, 2, 9, 5, 6, 4, 1, 3, 8]
[1, 3, 6, 7, 9, 8, 2, 4, 5]
[3, 7, 2, 6, 8, 9, 5, 1, 4]
[8, 1, 4, 2, 5, 3, 7, 6, 9]
[6, 9, 5, 4, 1, 7, 3, 8, 2]


Functions:

solve_sudoku: solves the board in place with backtracking, returns true if solved and false if no solution exists.

find_empty_cell: returns the row and column of the first empty cell or none if the puzzle is complete.

is_valid: checks if an input number is valid.

assess_difficulty: returns the difficulty based on the number of nodes searched. 



Difficulty Ratings:
Easy: 10 or less nodes searched
Medium: 11 -300 nodes searched
Hard: 300 or more nodes searched