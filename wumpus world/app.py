import os
import random
from flask import Flask, jsonify, request, render_template
from typing import Set, Tuple, List, Dict
from kb import Clause, KnowledgeBase

app = Flask(__name__)

class LogicProcessor:
    def __init__(self) -> None:
        self.kb_instance = KnowledgeBase()

    def submit_clause(self, c: Clause) -> None:
        self.kb_instance.add_clause(c)

    def verify_safety(self, prop: str, is_not: bool = False) -> bool:
        return self.kb_instance.entails(prop, is_not)

# --- GLOBAL APPLICATION STATE ---
world_state: Dict = {}
agent_coordinates: Tuple[int, int] = None
step_counter: int = 0
active_percepts: str = "None"
safe_tiles: Set[Tuple[int, int]] = set()
visited_tiles: Set[Tuple[int, int]] = set()
logic_engine = LogicProcessor()
is_active: bool = False

def build_simulation(r: int, c: int) -> dict:
    global world_state, agent_coordinates, step_counter, active_percepts, safe_tiles, visited_tiles, logic_engine, is_active
    
    slots = [(row, col) for row in range(r) for col in range(c) if (row, col) != (0, 0)]
    
    pit_locations = set(random.sample(slots, 2))
    available = [s for s in slots if s not in pit_locations]
    
    wumpus_loc = random.choice(available)
    available.remove(wumpus_loc)
    
    gold_loc = random.choice(available)
    
    world_state = {
        "rows": r, "cols": c,
        "pits": [{'row': r_idx, 'col': c_idx} for r_idx, c_idx in pit_locations],
        "wumpus": {'row': wumpus_loc[0], 'col': wumpus_loc[1]},
        "gold": {'row': gold_loc[0], 'col': gold_loc[1]}
    }
    
    agent_coordinates = (0, 0)
    step_counter = 0
    active_percepts = "None"
    safe_tiles = set()
    visited_tiles = {agent_coordinates}
    logic_engine = LogicProcessor()
    is_active = True
    
    # Starting coordinates are safe by definition
    logic_engine.submit_clause(Clause([("P_0_0", True)]))
    logic_engine.submit_clause(Clause([("W_0_0", True)]))
    
    refresh_percept_data()
    return world_state

def locate_neighbors(pos: Tuple[int, int], r_max: int, c_max: int) -> List[Tuple[int, int]]:
    r, c = pos
    neighbors = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < r_max and 0 <= nc < c_max:
            neighbors.append((nr, nc))
    return neighbors

def refresh_percept_data() -> None:
    global agent_coordinates, active_percepts, step_counter, safe_tiles, visited_tiles

    r_limit, c_limit = world_state["rows"], world_state["cols"]
    pits = [(p['row'], p['col']) for p in world_state["pits"]]
    wumpus = (world_state["wumpus"]["row"], world_state["wumpus"]["col"])
    gold = (world_state["gold"]["row"], world_state["gold"]["col"])

    adj_tiles = locate_neighbors(agent_coordinates, r_limit, c_limit)

    breeze = any(tile in pits for tile in adj_tiles)
    stench = any(tile == wumpus for tile in adj_tiles)
    glitter = (agent_coordinates == gold) 
    
    active_percepts = f"Breeze: {breeze}, Stench: {stench}, Glitter: {glitter}"

    if breeze:
        logic_engine.submit_clause(Clause([(f"P_{r}_{c}", False) for r, c in adj_tiles]))
    else:
        for r, c in adj_tiles: logic_engine.submit_clause(Clause([(f"P_{r}_{c}", True)]))

    if stench:
        logic_engine.submit_clause(Clause([(f"W_{r}_{c}", False) for r, c in adj_tiles]))
    else:
        for r, c in adj_tiles: logic_engine.submit_clause(Clause([(f"W_{r}_{c}", True)]))

    unexplored = [tile for tile in adj_tiles if tile not in visited_tiles]
    safe_tiles = set()
    
    for (r, c) in unexplored:
        is_pit_safe = logic_engine.verify_safety(f"P_{r}_{c}", is_not=True)
        is_wumpus_safe = logic_engine.verify_safety(f"W_{r}_{c}", is_not=True)
        step_counter += 2 

        if is_pit_safe and is_wumpus_safe:
            safe_tiles.add((r, c))

def trigger_movement(cmd: str) -> Tuple[Dict, int]:
    global agent_coordinates, active_percepts, visited_tiles, is_active

    if not is_active:
        return {"error": "Session inactive."}, 400

    dy, dx = 0, 0
    if cmd == "up": dy = -1
    elif cmd == "down": dy = 1
    elif cmd == "left": dx = -1
    elif cmd == "right": dx = 1

    ny, nx = agent_coordinates[0] + dy, agent_coordinates[1] + dx
    if not (0 <= ny < world_state["rows"] and 0 <= nx < world_state["cols"]):
        return {"error": "Boundary hit"}, 400

    agent_coordinates = (ny, nx)
    visited_tiles.add(agent_coordinates)

    p_list = [(p['row'], p['col']) for p in world_state["pits"]]
    w_loc = (world_state["wumpus"]["row"], world_state["wumpus"]["col"])
    g_loc = (world_state["gold"]["row"], world_state["gold"]["col"])

    if agent_coordinates == g_loc:
        is_active = False
        return {
            "agent_pos": {"row": ny, "col": nx},
            "game_over": True, "victory": True, "death_reason": "Asset Secured!",
            "inference_steps": step_counter, "current_percepts": "Glitter: True",
            "safe_cells": [], "visited_cells": [{"row": r, "col": c} for r, c in visited_tiles]
        }, 200

    if agent_coordinates in p_list or agent_coordinates == w_loc:
        is_active = False
        msg = "Fatal Fall into Pit" if agent_coordinates in p_list else "Terminated by Wumpus"
        return {
            "agent_pos": {"row": ny, "col": nx},
            "game_over": True, "victory": False, "death_reason": msg,
            "inference_steps": step_counter, "current_percepts": "SIGNAL LOST",
            "safe_cells": [], "visited_cells": [{"row": r, "col": c} for r, c in visited_tiles]
        }, 200

    refresh_percept_data()

    return {
        "agent_pos": {"row": ny, "col": nx},
        "game_over": False,
        "inference_steps": step_counter,
        "current_percepts": active_percepts,
        "safe_cells": [{"row": r, "col": c} for r, c in safe_tiles],
        "visited_cells": [{"row": r, "col": c} for r, c in visited_tiles]
    }, 200

app = Flask(__name__)

@app.route("/")
def entry_point():
    return render_template("index.html")

@app.route("/create_grid", methods=["POST"])
def setup_grid() -> dict:
    req = request.get_json() or {}
    data = build_simulation(req.get("rows", 5), req.get("cols", 5))
    return jsonify({"status": "success", "grid": data})

@app.route("/move", methods=["POST"])
def move_handler() -> dict:
    action = request.get_json().get("action")
    res, code = trigger_movement(action)
    return jsonify(res), code

app = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)