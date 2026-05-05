import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random
import math

class AgarEnv(gym.Env):
    def __init__(self):
        super(AgarEnv, self).__init__()
        self.action_space = spaces.Box(low=-1, high=1, shape=(2,), dtype=np.float32)
        
        self.bounds_x = 3000
        self.bounds_y = 3000
        self.num_food = 400
        self.num_players = 16 
        self.reset()

    def reset(self, seed=None, options=None):
        self.players = []
        for i in range(self.num_players):
            self.players.append({
                "pos": [random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)],
                "r": 15.0,
                "target_food": random.randint(0, self.num_food - 1) # Assign target to save CPU
            })
            
        # Food is now a simple list of lists for speed
        self.food = [[random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)] for _ in range(self.num_food)]
        return self._get_obs(), {}

    def step(self, action):
        # 1. MOVE HUMAN
        norm = math.hypot(action[0], action[1])
        if norm > 0:
            action = action / norm 
        speed = max(1.0, 100.0 / self.players[0]["r"])
        self.players[0]["pos"][0] += action[0] * speed
        self.players[0]["pos"][1] += action[1] * speed

        # 2. MOVE BOTS (Optimized)
        for i in range(1, self.num_players):
            bot = self.players[i]
            bx, by = bot["pos"][0], bot["pos"][1]
            bot_r = bot["r"]
            
            move_vec_x, move_vec_y = 0.0, 0.0
            
            # FAST FOOD SEARCH: Bots just go to their assigned food
            tf_idx = bot.get("target_food", 0)
            if tf_idx >= len(self.food):
                tf_idx = random.randint(0, max(0, len(self.food)-1))
                bot["target_food"] = tf_idx
                
            if len(self.food) > 0:
                target_f = self.food[tf_idx]
                fx, fy = target_f[0] - bx, target_f[1] - by
                fn = math.hypot(fx, fy)
                if fn > 0:
                    move_vec_x += (fx / fn)
                    move_vec_y += (fy / fn)

            # FAST PLAYER AVOIDANCE/CHASING (Using squared distance)
            for j in range(self.num_players):
                if i == j: continue
                other = self.players[j]
                ox, oy = other["pos"][0], other["pos"][1]
                
                dx = ox - bx
                dy = oy - by
                dist_sq = dx*dx + dy*dy
                
                if 0 < dist_sq < 250000:  # 500 squared (bot vision radius)
                    dist = math.sqrt(dist_sq)
                    if other["r"] > bot_r * 1.1:
                        # Flee
                        move_vec_x -= (dx / dist) * (1000.0 / dist)
                        move_vec_y -= (dy / dist) * (1000.0 / dist)
                    elif bot_r > other["r"] * 1.1:
                        # Chase
                        move_vec_x += (dx / dist) * (400.0 / dist)
                        move_vec_y += (dy / dist) * (400.0 / dist)
            
            mn = math.hypot(move_vec_x, move_vec_y)
            if mn > 0:
                final_action_x = move_vec_x / mn
                final_action_y = move_vec_y / mn
            else:
                final_action_x = random.uniform(-1, 1)
                final_action_y = random.uniform(-1, 1)
                
            bot_speed = max(1.0, 100.0 / bot_r)
            bot["pos"][0] += final_action_x * bot_speed
            bot["pos"][1] += final_action_y * bot_speed

        # 3. BOUNDARIES
        for p in self.players:
            p["pos"][0] = max(0, min(p["pos"][0], self.bounds_x))
            p["pos"][1] = max(0, min(p["pos"][1], self.bounds_y))

        # 4. FAST FOOD EATING (Squared dist)
        new_food = []
        for f in self.food:
            fx, fy = f[0], f[1]
            eaten = False
            for p in self.players:
                # dx^2 + dy^2 < r^2
                if (p["pos"][0] - fx)**2 + (p["pos"][1] - fy)**2 < p["r"]**2:
                    p["r"] += 0.5
                    eaten = True
                    break
            
            if eaten:
                new_food.append([random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)])
            else:
                new_food.append(f)
        self.food = new_food

        # 5. FAST PLAYER EATING
        for i in range(self.num_players):
            for j in range(i + 1, self.num_players):
                p1 = self.players[i]
                p2 = self.players[j]
                dist_sq = (p1["pos"][0] - p2["pos"][0])**2 + (p1["pos"][1] - p2["pos"][1])**2
                
                if p1["r"] > p2["r"] * 1.1 and dist_sq < p1["r"]**2:
                    p1["r"] = math.sqrt(p1["r"]**2 + p2["r"]**2)
                    p2["pos"] = [random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)]
                    p2["r"] = 15.0
                elif p2["r"] > p1["r"] * 1.1 and dist_sq < p2["r"]**2:
                    p2["r"] = math.sqrt(p2["r"]**2 + p1["r"]**2)
                    p1["pos"] = [random.uniform(0, self.bounds_x), random.uniform(0, self.bounds_y)]
                    p1["r"] = 15.0

        return self._get_obs(), 0, False, False, {}

    def _get_obs(self):
        # OPTIMIZATION: Round variables to 1 decimal to shrink JSON size over network by 70%
        human = {"x": round(self.players[0]["pos"][0], 1), "y": round(self.players[0]["pos"][1], 1), "r": round(self.players[0]["r"], 1)}
        bots = [{"x": round(p["pos"][0], 1), "y": round(p["pos"][1], 1), "r": round(p["r"], 1)} for p in self.players[1:]]
        
        return {
            "human": human,
            "bots": bots,
            "food": [[round(f[0], 1), round(f[1], 1)] for f in self.food], # Sending arrays instead of dicts
            "map": {"width": self.bounds_x, "height": self.bounds_y}
        }