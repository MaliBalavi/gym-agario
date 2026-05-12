import random
import math

class AgarEngine:
    def __init__(self):
        self.bounds_x = 3000
        self.bounds_y = 3000
        self.num_food = 400
        self.food = [[random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)] for _ in range(self.num_food)]
        self.players = {} 
        self.actions = {} 
        
        for i in range(15):
            self.add_bot(f"bot_{i}")

    def add_bot(self, bot_id):
        self.players[bot_id] = {
            "name": f"Bot {bot_id.split('_')[1]}",
            "is_bot": True,
            "cells": [{"pos": [random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)], "r": 15.0, "boost": [0,0], "cooldown": 0}],
            "target_food": random.randint(0, self.num_food - 1)
        }

    def add_human(self, sid, username):
        self.players[sid] = {
            "name": username,
            "is_bot": False,
            "cells": [{"pos": [random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)], "r": 15.0, "boost": [0,0], "cooldown": 0}]
        }
        self.actions[sid] = [0.0, 0.0, False] 

    def remove_human(self, sid):
        self.players.pop(sid, None)
        self.actions.pop(sid, None)

    def set_action(self, sid, dx, dy, split=False):
        if sid in self.actions:
            current_split = self.actions[sid][2]
            self.actions[sid] = [dx, dy, current_split or split]

    def step(self):
        # 1. KRETANJE I RAZDVAJANJE (Optimizovana matematika)
        for pid, p in list(self.players.items()):
            if p["is_bot"]:
                for c in p["cells"]:
                    move_vec_x, move_vec_y = 0.0, 0.0
                    bx, by = c["pos"][0], c["pos"][1]
                    
                    # Sigurna provera hrane za bota
                    if not self.food: continue
                    tf_idx = p.get("target_food", 0) % len(self.food)
                    
                    fx, fy = self.food[tf_idx][0] - bx, self.food[tf_idx][1] - by
                    fn = math.hypot(fx, fy)
                    if fn > 0: 
                        move_vec_x, move_vec_y = fx/fn, fy/fn

                    # Brzo izbegavanje / napad
                    for other_id, other_p in self.players.items():
                        if pid == other_id: continue
                        for oc in other_p["cells"]:
                            dx, dy = oc["pos"][0] - bx, oc["pos"][1] - by
                            if abs(dx) > 1000 or abs(dy) > 1000: continue
                            
                            dist_sq = dx*dx + dy*dy
                            if 0 < dist_sq < 250000:
                                dist = math.sqrt(dist_sq)
                                if oc["r"] > c["r"] * 1.1:
                                    move_vec_x -= (dx / dist) * (1000.0 / dist)
                                    move_vec_y -= (dy / dist) * (1000.0 / dist)
                                elif c["r"] > oc["r"] * 1.1:
                                    move_vec_x += (dx / dist) * (400.0 / dist)
                                    move_vec_y += (dy / dist) * (400.0 / dist)
                                    
                    mn = math.hypot(move_vec_x, move_vec_y)
                    if mn > 0: 
                        move_vec_x, move_vec_y = move_vec_x/mn, move_vec_y/mn
                    
                    speed = max(1.0, 100.0 / c["r"])
                    c["pos"][0] += move_vec_x * speed + c["boost"][0]
                    c["pos"][1] += move_vec_y * speed + c["boost"][1]
                    c["boost"][0] *= 0.9
                    c["boost"][1] *= 0.9

            else:
                dx, dy, split = self.actions.get(pid, [0.0, 0.0, False])
                
                if split:
                    new_cells = []
                    for c in p["cells"]:
                        if c["r"] > 25 and (len(p["cells"]) + len(new_cells)) < 16:
                            c["r"] /= 1.414 
                            c["cooldown"] = 300 
                            norm = math.hypot(dx, dy)
                            b_dx, b_dy = (dx/norm, dy/norm) if norm > 0 else (1, 0)
                            
                            new_cells.append({
                                "pos": [c["pos"][0], c["pos"][1]],
                                "r": c["r"],
                                "boost": [b_dx * 20, b_dy * 20], # Smanjen i stabilizovan boost
                                "cooldown": 300
                            })
                    p["cells"].extend(new_cells)
                    self.actions[pid][2] = False 

                for c in p["cells"]:
                    norm = math.hypot(dx, dy)
                    vx, vy = (dx/norm, dy/norm) if norm > 0 else (0, 0)
                        
                    speed = max(1.0, 100.0 / c["r"])
                    c["pos"][0] += vx * speed + c["boost"][0]
                    c["pos"][1] += vy * speed + c["boost"][1]
                    
                    c["boost"][0] *= 0.85
                    c["boost"][1] *= 0.85
                    if c["cooldown"] > 0: c["cooldown"] -= 1

            for c in p["cells"]:
                c["pos"][0] = max(0, min(c["pos"][0], self.bounds_x))
                c["pos"][1] = max(0, min(c["pos"][1], self.bounds_y))

        # 2. BRZO JEDENJE HRANE
        new_food = []
        for f in self.food:
            eaten = False
            for pid, p in self.players.items():
                for c in p["cells"]:
                    # Brzi provera kvadrata pre računanja Pitagore
                    if abs(c["pos"][0] - f[0]) < c["r"] and abs(c["pos"][1] - f[1]) < c["r"]:
                        if (c["pos"][0] - f[0])**2 + (c["pos"][1] - f[1])**2 < c["r"]**2:
                            c["r"] = math.sqrt(c["r"]**2 + 10) 
                            eaten = True
                            break
                if eaten: break
            if eaten:
                new_food.append([random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)])
            else:
                new_food.append(f)
        self.food = new_food

        # 3. SUDARI IGRAČA
        all_cells = [(pid, c) for pid, p in self.players.items() for c in p["cells"]]
        cells_to_remove = set() # Korišćenje seta za bržu proveru (O(1))

        for i in range(len(all_cells)):
            for j in range(i + 1, len(all_cells)):
                pid1, c1 = all_cells[i]
                pid2, c2 = all_cells[j]
                if id(c1) in cells_to_remove or id(c2) in cells_to_remove: continue

                dx = c1["pos"][0] - c2["pos"][0]
                dy = c1["pos"][1] - c2["pos"][1]
                if abs(dx) > (c1["r"] + c2["r"]) or abs(dy) > (c1["r"] + c2["r"]): continue
                
                dist_sq = dx*dx + dy*dy
                dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.1

                if pid1 == pid2:
                    if c1["cooldown"] <= 0 and c2["cooldown"] <= 0:
                        if dist < max(c1["r"], c2["r"]): 
                            c1["r"] = math.sqrt(c1["r"]**2 + c2["r"]**2)
                            cells_to_remove.add(id(c2))
                    else:
                        overlap = (c1["r"] + c2["r"]) - dist
                        if overlap > 0: 
                            px = (dx/dist) * (overlap * 0.1)
                            py = (dy/dist) * (overlap * 0.1)
                            c1["pos"][0] += px
                            c1["pos"][1] += py
                            c2["pos"][0] -= px
                            c2["pos"][1] -= py
                else:
                    if c1["r"] > c2["r"] * 1.1 and dist < c1["r"]:
                        c1["r"] = math.sqrt(c1["r"]**2 + c2["r"]**2)
                        cells_to_remove.add(id(c2))
                    elif c2["r"] > c1["r"] * 1.1 and dist < c2["r"]:
                        c2["r"] = math.sqrt(c2["r"]**2 + c1["r"]**2)
                        cells_to_remove.add(id(c1))

        for pid, p in self.players.items():
            p["cells"] = [c for c in p["cells"] if id(c) not in cells_to_remove]
            if not p["cells"]:
                self.respawn(p)

    def respawn(self, p):
        p["cells"] = [{"pos": [random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)], "r": 15.0, "boost": [0,0], "cooldown": 0}]

    def get_partial_state(self, sid):
        if sid not in self.players: return None
        me = self.players[sid]
        
        if not me["cells"]: return None
        
        sum_x = sum(c["pos"][0] * (c["r"]**2) for c in me["cells"])
        sum_y = sum(c["pos"][1] * (c["r"]**2) for c in me["cells"])
        total_area = sum(c["r"]**2 for c in me["cells"])
        
        px = sum_x / total_area
        py = sum_y / total_area
        
        combined_r = math.sqrt(total_area)
        zoom = max(math.pow(15 / combined_r, 0.4), 0.1)
        view_w = (1000 / zoom) / 2 + 100
        view_h = (800 / zoom) / 2 + 100

        out_players = {}
        for pid, p in self.players.items():
            out_cells = []
            for c in p["cells"]:
                if abs(c["pos"][0] - px) < view_w + c["r"] and abs(c["pos"][1] - py) < view_h + c["r"]:
                    # MREŽNA OPTIMIZACIJA: Šaljemo NIZ [x, y, r] umesto rečnika
                    out_cells.append([round(c["pos"][0], 1), round(c["pos"][1], 1), round(c["r"], 1)])
            if out_cells:
                out_players[pid] = {"n": p["name"], "b": p["is_bot"], "c": out_cells} # Kratka imena ključeva
                
        out_food = [[round(f[0], 1), round(f[1], 1)] for f in self.food if abs(f[0] - px) < view_w and abs(f[1] - py) < view_h]
                
        leaderboard = [{"id": pid, "n": p["name"], "s": int(math.sqrt(sum(c["r"]**2 for c in p["cells"])))} for pid, p in self.players.items()]
        leaderboard.sort(key=lambda x: x["s"], reverse=True)
        
        return {"p": out_players, "f": out_food, "l": leaderboard[:10], "m": [self.bounds_x, self.bounds_y]}