"""Validación de pistas y búsqueda acotada de hasta dos soluciones."""
from time import monotonic


def parse_board(value):
    if not isinstance(value, list) or len(value) != 9:
        raise ValueError("El tablero debe tener nueve filas.")
    if any(not isinstance(row, list) or len(row) != 9 for row in value):
        raise ValueError("Cada fila debe tener nueve casillas.")
    if any(type(n) is not int or not 0 <= n <= 9 for row in value for n in row):
        raise ValueError("Introduce números del 1 al 9 o deja la casilla vacía.")
    return [row[:] for row in value]


def conflicts(board):
    groups = (
        [[(r, c) for c in range(9)] for r in range(9)]
        + [[(r, c) for r in range(9)] for c in range(9)]
        + [[(r, c) for r in range(y, y + 3) for c in range(x, x + 3)]
           for y in (0, 3, 6) for x in (0, 3, 6)]
    )
    found = set()
    for group in groups:
        values = {}
        for r, c in group:
            if board[r][c]:
                values.setdefault(board[r][c], []).append((r, c))
        for positions in values.values():
            if len(positions) > 1:
                found.update(positions)
    return [list(p) for p in sorted(found)]


def solve_board(value, *, timeout=1.5, max_nodes=80000):
    board = parse_board(value)
    bad = conflicts(board)
    if bad:
        return {"status": "conflict", "conflicts": bad,
                "message": "Hay números repetidos en una fila, columna o bloque. Revisa las casillas marcadas."}
    if not any(n for row in board for n in row):
        return {"status": "insufficient", "message": "Introduce las pistas del Sudoku antes de resolver."}
    solutions = []
    started = monotonic()
    nodes = 0
    limited = False

    def search():
        nonlocal nodes, limited
        nodes += 1
        if nodes > max_nodes or monotonic() - started > timeout:
            limited = True
            return
        best = None
        options = None
        for r in range(9):
            for c in range(9):
                if board[r][c]:
                    continue
                used = set(board[r]) | {board[i][c] for i in range(9)}
                used |= {board[y][x] for y in range(r // 3 * 3, r // 3 * 3 + 3)
                         for x in range(c // 3 * 3, c // 3 * 3 + 3)}
                available = [n for n in range(1, 10) if n not in used]
                if not available:
                    return
                if options is None or len(available) < len(options):
                    best, options = (r, c), available
                    if len(options) == 1:
                        break
            if options is not None and len(options) == 1:
                break
        if best is None:
            solutions.append([row[:] for row in board])
            return
        r, c = best
        for n in options:
            board[r][c] = n
            search()
            board[r][c] = 0
            if limited or len(solutions) >= 2:
                return

    search()
    meta = {"nodes": nodes, "seconds": round(monotonic() - started, 4)}
    if limited:
        return dict(meta, status="limit", message="No se ha podido verificar la solución dentro del límite de cálculo. Revisa las pistas.")
    if not solutions:
        return dict(meta, status="unsolvable", message="Estas pistas no tienen solución. Comprueba los números de la imagen.")
    if len(solutions) > 1:
        return dict(meta, status="multiple", message="Hay más de una solución. Puede faltar alguna pista; revisa el tablero.")
    return dict(meta, status="solved", solution=solutions[0],
                message="Solución única para las pistas introducidas.")
