#-------24F-0613---------
from flask import Flask, jsonify, request, render_template
import random
from typing import Set, Tuple, List, Dict
from kb import Clause, KnowledgeBase

class InferenceEngine:
    def __init__(self) -> None:
        self.kb = KnowledgeBase()

    def add_clause(self, clause: Clause) -> None:
        self.kb.add_clause(clause)

    def entails(self, proposition: str, negated: bool = False) -> bool:
        return self.kb.entails(proposition, negated)

# Global states
grid_data: Dict = {}
agent_pos: Tuple[int, int] = None
inference_steps: int = 0
current_percepts: str = "None"
safe_cells: Set[Tuple[int, int]] = set()
visited_cells: Set[Tuple[int, int]] = set()
inference_engine = InferenceEngine()
game_active: bool = False

def create_grid(rows: int, cols: int) -> dict:
    global grid_data, agent_pos, inference_steps, current_percepts, safe_cells, visited_cells, inference_engine, game_active
    
    cells = [(r, c) for r in range(rows) for c in range(cols) if (r, c) != (0, 0)]
    
    pits = set(random.sample(cells, 2))
    remaining = [c for c in cells if c not in pits]
    
    wumpus = random.choice(remaining)
    remaining.remove(wumpus)
    
    gold = random.choice(remaining)
    
    grid_data = {
        "rows": rows, "cols": cols,
        "pits": [{'row': r, 'col': c} for r, c in pits],
        "wumpus": {'row': wumpus[0], 'col': wumpus[1]},
        "gold": {'row': gold[0], 'col': gold[1]}
    }
    
    agent_pos = (0, 0)
    inference_steps = 0
    current_percepts = "None"
    safe_cells = set()
    visited_cells = {agent_pos}
    inference_engine = InferenceEngine()
    game_active = True
    
    inference_engine.add_clause(Clause([("P_0_0", True)]))
    inference_engine.add_clause(Clause([("W_0_0", True)]))
    
    update_percepts_and_safe_moves()
    return grid_data

def get_adjacent(pos: Tuple[int, int], rows: int, cols: int) -> List[Tuple[int, int]]:
    r, c = pos
    adjacent = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            adjacent.append((nr, nc))
    return adjacent

def update_percepts_and_safe_moves() -> None:
    global agent_pos, current_percepts, inference_steps, safe_cells, visited_cells

    rows, cols = grid_data["rows"], grid_data["cols"]
    pits = [(p['row'], p['col']) for p in grid_data["pits"]]
    wumpus = (grid_data["wumpus"]["row"], grid_data["wumpus"]["col"])
    gold = (grid_data["gold"]["row"], grid_data["gold"]["col"])

    adj = get_adjacent(agent_pos, rows, cols)

    has_breeze = any(cell in pits for cell in adj)
    has_stench = any(cell == wumpus for cell in adj)
    has_glitter = (agent_pos == gold) 
    
    current_percepts = f"Breeze: {has_breeze}, Stench: {has_stench}, Glitter: {has_glitter}"

    if has_breeze:
        inference_engine.add_clause(Clause([(f"P_{r}_{c}", False) for r, c in adj]))
    else:
        for r, c in adj: inference_engine.add_clause(Clause([(f"P_{r}_{c}", True)]))

    if has_stench:
        inference_engine.add_clause(Clause([(f"W_{r}_{c}", False) for r, c in adj]))
    else:
        for r, c in adj: inference_engine.add_clause(Clause([(f"W_{r}_{c}", True)]))

    unvisited_adj = [cell for cell in adj if cell not in visited_cells]
    safe_cells = set()
    
    for (r, c) in unvisited_adj:
        pit_safe = inference_engine.entails(f"P_{r}_{c}", negated=True)
        wumpus_safe = inference_engine.entails(f"W_{r}_{c}", negated=True)
        inference_steps += 2 

        if pit_safe and wumpus_safe:
            safe_cells.add((r, c))

def move_agent(action: str) -> Tuple[Dict, int]:
    global agent_pos, current_percepts, visited_cells, game_active

    if not game_active:
        return {"error": "Game is already over. Generate a new world."}, 400

    dr, dc = 0, 0
    if action == "up": dr = -1
    elif action == "down": dr = 1
    elif action == "left": dc = -1
    elif action == "right": dc = 1

    nr, nc = agent_pos[0] + dr, agent_pos[1] + dc
    if not (0 <= nr < grid_data["rows"] and 0 <= nc < grid_data["cols"]):
        return {"error": "Move would take agent outside grid"}, 400

    agent_pos = (nr, nc)
    visited_cells.add(agent_pos)

    # Validate Win / Death States
    pits = [(p['row'], p['col']) for p in grid_data["pits"]]
    wumpus = (grid_data["wumpus"]["row"], grid_data["wumpus"]["col"])
    gold = (grid_data["gold"]["row"], grid_data["gold"]["col"])

    if agent_pos == gold:
        game_active = False
        return {
            "agent_pos": {"row": agent_pos[0], "col": agent_pos[1]},
            "game_over": True, "victory": True, "death_reason": "Secured the Gold!",
            "inference_steps": inference_steps, "current_percepts": "Glitter: True",
            "safe_cells": [], "visited_cells": [{"row": r, "col": c} for r, c in visited_cells]
        }, 200

    if agent_pos in pits or agent_pos == wumpus:
        game_active = False
        reason = "Fell into a bottomless pit!" if agent_pos in pits else "Eaten alive by the Wumpus!"
        return {
            "agent_pos": {"row": agent_pos[0], "col": agent_pos[1]},
            "game_over": True, "victory": False, "death_reason": reason,
            "inference_steps": inference_steps, "current_percepts": "DEAD",
            "safe_cells": [], "visited_cells": [{"row": r, "col": c} for r, c in visited_cells]
        }, 200

    update_percepts_and_safe_moves()

    return {
        "agent_pos": {"row": agent_pos[0], "col": agent_pos[1]},
        "game_over": False,
        "inference_steps": inference_steps,
        "current_percepts": current_percepts,
        "safe_cells": [{"row": r, "col": c} for r, c in safe_cells],
        "visited_cells": [{"row": r, "col": c} for r, c in visited_cells]
    }, 200

app = Flask(__name__)

@app.route("/")
def serve_frontend():
    return render_template("index.html")

@app.route("/create_grid", methods=["POST"])
def create_grid_route() -> dict:
    data = request.get_json() or {}
    grid = create_grid(data.get("rows", 5), data.get("cols", 5))
    return jsonify({"message": "Grid created", "grid": grid})

@app.route("/move", methods=["POST"])
def move_route() -> dict:
    action = request.get_json().get("action")
    result, status_code = move_agent(action)
    return jsonify(result), status_code

if __name__ == "__main__":
    app.run(debug=True)