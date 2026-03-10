import json
import random
import sys
import os
from typing import List, Dict, Tuple

# Import the single source of truth for game logic
from game_logic import (
    GRID_WIDTH, GRID_HEIGHT, PIECE_SHAPES, simulate_step_by_step_execution,
    get_col_heights, count_holes, calculate_bumpiness, get_max_height, get_wells_depth,
    get_piece_start_position
)

# --- Constants and Configuration (优化版) ---
POPULATION_SIZE = 50  # 增加种群规模
ELITISM_COUNT = 15    # 增加精英保留数量
BREEDING_POOL_SIZE = 25  # 增加繁殖池大小
MUTATION_RATE = 0.15  # 增加变异率以增加多样性
MUTATION_AMOUNT = 0.3  # 增加变异幅度
BEST_AGENT_PATH = 'best_genetic_agent.json'

# 新增：消行目标相关的参数
TARGET_LINES = 1000   # 目标平均消行数
LINES_REWARD_FACTOR = 10  # 消行奖励系数

# --- Piece Definitions (Aligned with frontend a standard representation) ---
# This is now imported from game_logic.py
# PIECES = {
#     "I": [[1, 1, 1, 1]],
#     "J": [[2, 0, 0], [2, 2, 2]],
#     "L": [[0, 0, 3], [3, 3, 3]],
#     "S": [[0, 5, 5], [5, 5, 0]],
#     "Z": [[7, 7, 0], [0, 7, 7]],
#     "T": [[0, 6, 0], [6, 6, 6]],
#     "O": [[4, 4], [4, 4]]
# }


# ==============================================================================
#  GAME PHYSICS LOGIC (Strictly aligned with 方块new/static/tetris.js)
# ==============================================================================

# All physics functions are now imported from game_logic.py to ensure consistency

# ==============================================================================
#  AGENT AND TRAINING LOGIC (Using the Shared Physics Engine)
# ==============================================================================

class TetrisGame:
    def __init__(self):
        self.board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.lines_cleared = 0
        self.level = 1 # Added level tracking
        self.game_over = False
        self.piece_pool = []
        self.current_piece_name = self.new_piece_name()
        self.current_piece_shape = PIECE_SHAPES[self.current_piece_name]

    def new_piece_name(self):
        """
        Generates a new piece with pure randomness, matching the frontend logic.
        """
        return random.choice(list(PIECE_SHAPES.keys()))
    
    def step(self, move):
        if self.game_over:
            return

        # 使用新的逐步执行模拟，与前端完全一致
        board_after_move, lines = simulate_step_by_step_execution(
            self.board, 
            self.current_piece_shape, 
            move['rotation'], 
            move['x']
        )
        
        if board_after_move is None:
            self.game_over = True
            return

        self.board = board_after_move
        self.lines_cleared += lines
        
        # Scoring logic aligned with frontend (tetris.js)
        if lines > 0:
            line_scores = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += line_scores.get(lines, 0) * self.level
            self.level = (self.lines_cleared // 10) + 1
        
        self.current_piece_name = self.new_piece_name()
        self.current_piece_shape = PIECE_SHAPES[self.current_piece_name]
        
        # Check for game over on new piece spawn - 使用统一的起始位置计算
        start_x, start_y = get_piece_start_position(self.current_piece_shape)
        from game_logic import check_collision
        if check_collision(self.board, self.current_piece_shape, start_x, start_y):
            self.game_over = True

class GeneticAgent:
    def __init__(self, weights=None):
        # 优化权重初始化范围，更适合长期消行策略
        self.weights = {
            "weight_height": random.uniform(-0.8, -0.2),        # 避免堆得太高
            "weight_line_completed": random.uniform(0.5, 1.5),  # 强化消行奖励
            "weight_holes": random.uniform(-1.2, -0.3),         # 强烈惩罚空洞
            "weight_bumpiness": random.uniform(-0.8, -0.1),     # 保持平整
            "weight_max_height": random.uniform(-1.0, -0.2),    # 控制最大高度
            "weight_wells": random.uniform(-0.8, -0.1),         # 避免深井
        }
        if weights:
            self.weights.update(weights)
        self.fitness = 0
        self.lines_cleared = 0  # 添加这个属性

    def get_fitness(self, board, lines_cleared):
        # 基础评分
        base_score = (
            self.weights["weight_height"] * sum(get_col_heights(board)) +
            self.weights["weight_holes"] * count_holes(board) +
            self.weights["weight_bumpiness"] * calculate_bumpiness(board) +
            self.weights["weight_line_completed"] * lines_cleared +
            self.weights["weight_max_height"] * get_max_height(board) +
            self.weights["weight_wells"] * get_wells_depth(board)
        )
        return base_score
    
    def get_enhanced_fitness(self, game_score, lines_cleared):
        """
        增强的fitness函数，更重视消行能力和长期生存
        """
        # 基础分数权重降低
        base_score_weight = 0.3
        
        # 消行奖励 - 非线性增长
        lines_bonus = 0
        if lines_cleared > 0:
            # 消行数越多，奖励越高（二次增长）
            lines_bonus = lines_cleared * LINES_REWARD_FACTOR * (1 + lines_cleared / TARGET_LINES)
            
            # 达到目标消行数的额外奖励
            if lines_cleared >= TARGET_LINES:
                lines_bonus *= 2  # 双倍奖励
        
        # 生存时间奖励（基于分数推算）
        survival_bonus = (game_score / 1000) * 0.5
        
        # 综合fitness
        total_fitness = (game_score * base_score_weight) + lines_bonus + survival_bonus
        
        return total_fitness

    def find_best_move(self, game: TetrisGame):
        best_score = float('-inf')
        best_move = None
        
        # 使用与simple_heuristic_ai.py完全相同的搜索逻辑
        for rotation_count in range(4):
            for target_x in range(-3, GRID_WIDTH + 3):  # 与AI相同的搜索范围
                
                board_after_move, lines_cleared = simulate_step_by_step_execution(
                    game.board, game.current_piece_shape, rotation_count, target_x
                )
                
                if board_after_move is None:
                    continue
                
                score = self.get_fitness(board_after_move, lines_cleared)
                
                if score > best_score:
                    best_score = score
                    best_move = {"rotation": rotation_count, "x": target_x}
        
        return best_move if best_move is not None else {"rotation": 0, "x": 5}

    def crossover(self, other_agent):
        child_weights = {}
        for key in self.weights:
            child_weights[key] = random.choice([self.weights[key], other_agent.weights[key]])
        child = GeneticAgent(weights=child_weights)
        child.mutate()
        return child

    def mutate(self):
        for key in self.weights:
            if random.random() < MUTATION_RATE:
                self.weights[key] += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)

    def save_weights(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.weights, f, indent=4)

    def load_weights(self, file_path):
        with open(file_path, 'r') as f:
            loaded_weights = json.load(f)
            self.weights.update(loaded_weights)

def run_generation(population, generation):
    games = [TetrisGame() for _ in range(POPULATION_SIZE)]
    
    while any(not game.game_over for game in games):
        for i, agent in enumerate(population):
            if not games[i].game_over:
                move = agent.find_best_move(games[i])
                games[i].step(move)

    for agent, game in zip(population, games):
        # 使用新的增强fitness函数，更重视消行能力
        agent.fitness = agent.get_enhanced_fitness(game.score, game.lines_cleared)
        agent.lines_cleared = game.lines_cleared  # 保存消行数据

    # 按fitness排序
    population.sort(key=lambda x: x.fitness, reverse=True)
    
    # 打印本代的统计信息
    best_fitness = population[0].fitness
    avg_fitness = sum(agent.fitness for agent in population) / len(population)
    avg_lines = sum(agent.lines_cleared for agent in population) / len(population)
    print(f"Generation {generation}: Best={best_fitness:.2f}, Avg={avg_fitness:.2f}, AvgLines={avg_lines:.1f}")
    
    return population

def main():
    game_stats = type('GameStats', (object,), {
        'top_score': 0, 
        'top_lines': 0, 
        'best_avg_lines': 0,
        'prev_avg_lines': 0,  # 新增：上一代平均消行
        'prev_max_lines': 0   # 新增：上一代最高消行
    })()
    
    population = [GeneticAgent() for _ in range(POPULATION_SIZE)]
    if os.path.exists(BEST_AGENT_PATH):
        print(f"Loading best agent from {BEST_AGENT_PATH}...")
        best_weights = json.load(open(BEST_AGENT_PATH))
        for agent in population:
            agent.load_weights(BEST_AGENT_PATH)
            agent.mutate() # Add some variation to the loaded best
        population[0].weights = best_weights # Ensure the first one is the pure best

    generation = 1
    try:
        while True:
            print(f"--- Generation {generation} ---")
            run_generation(population, generation)
            
            population.sort(key=lambda x: x.fitness, reverse=True)
            best_agent = population[0]
            
            # 计算当代统计
            current_best_score = best_agent.fitness
            current_avg_lines = sum(agent.lines_cleared for agent in population) / POPULATION_SIZE
            agent_with_best_lines = max(population, key=lambda agent: agent.lines_cleared)
            current_best_lines = agent_with_best_lines.lines_cleared
            
            # 更新历史记录
            game_stats.top_score = max(game_stats.top_score, current_best_score)
            game_stats.top_lines = max(game_stats.top_lines, current_best_lines)
            game_stats.best_avg_lines = max(game_stats.best_avg_lines, current_avg_lines)
            
            # 检查是否应该更新最佳模型
            should_update_best = False
            update_reason = ""
            
            if generation == 1:
                # 第一代直接保存
                should_update_best = True
                update_reason = "首代保存"
            elif current_avg_lines > game_stats.prev_avg_lines:
                # 平均消行提升
                should_update_best = True
                update_reason = f"平均消行提升: {game_stats.prev_avg_lines:.1f} -> {current_avg_lines:.1f}"
            elif current_best_lines > game_stats.prev_max_lines:
                # 最高消行提升
                should_update_best = True
                update_reason = f"最高消行提升: {game_stats.prev_max_lines} -> {current_best_lines}"
            
            # 保存最佳智能体（仅在消行能力提升时）
            if should_update_best:
                if current_avg_lines > game_stats.prev_avg_lines:
                    # 如果平均消行提升，保存平均表现最好的智能体
                    # 这里我们选择fitness排序后的第一个，因为它代表了整体最佳
                    best_agent.save_weights(BEST_AGENT_PATH)
                    print(f"✅ 更新最佳模型: {update_reason}")
                elif current_best_lines > game_stats.prev_max_lines:
                    # 如果最高消行提升，保存消行最多的智能体
                    agent_with_best_lines.save_weights(BEST_AGENT_PATH)
                    print(f"✅ 更新最佳模型: {update_reason}")
            else:
                print(f"⏸️  保持当前模型: 平均消行{current_avg_lines:.1f}({game_stats.prev_avg_lines:.1f}), 最高消行{current_best_lines}({game_stats.prev_max_lines})")
            
            # 如果有高消行智能体，额外保存一份
            if current_best_lines >= TARGET_LINES:
                high_lines_path = f'best_lines_agent_{current_best_lines}.json'
                agent_with_best_lines.save_weights(high_lines_path)
                print(f"🎉 保存高消行智能体: {high_lines_path}")
            
            # 输出详细统计
            print(f"本代最高fitness: {current_best_score:.2f} | 历史最高fitness: {game_stats.top_score:.2f}")
            print(f"本代最高消行: {current_best_lines} | 历史最高消行: {game_stats.top_lines}")
            print(f"本代平均消行: {current_avg_lines:.1f} | 历史最高平均: {game_stats.best_avg_lines:.1f}")
            
            # 目标达成提示
            if current_avg_lines >= TARGET_LINES:
                print(f"🎯 目标达成！平均消行 {current_avg_lines:.1f} >= {TARGET_LINES}")
            else:
                progress = (current_avg_lines / TARGET_LINES) * 100
                print(f"📈 目标进度: {progress:.1f}% ({current_avg_lines:.1f}/{TARGET_LINES})")

            # 更新上一代记录
            game_stats.prev_avg_lines = current_avg_lines
            game_stats.prev_max_lines = current_best_lines

            next_gen_population = []
            next_gen_population.extend(population[:ELITISM_COUNT])
            
            breeding_pool = population[:BREEDING_POOL_SIZE]
            for _ in range(POPULATION_SIZE - ELITISM_COUNT):
                parent1 = random.choice(breeding_pool)
                parent2 = random.choice(breeding_pool)
                child = parent1.crossover(parent2)
                next_gen_population.append(child)
            
            population = next_gen_population
            generation += 1
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n🛑 训练停止。最佳智能体已保存。")
        print(f"最终统计: 最高消行={game_stats.top_lines}, 最高平均消行={game_stats.best_avg_lines:.1f}")
        sys.exit()

if __name__ == "__main__":
    main() 