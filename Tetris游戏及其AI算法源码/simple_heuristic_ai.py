import json
import os
from typing import List, Dict

# Import the single source of truth for game logic
from game_logic import (
    GRID_WIDTH, GRID_HEIGHT, PIECE_SHAPES, simulate_step_by_step_execution,
    get_col_heights, count_holes, calculate_bumpiness, get_max_height, get_wells_depth,
    get_piece_start_position
)

# --- Constants ---
WEIGHTS_FILE = 'best_genetic_agent.json'

# --- Load Trained Weights ---
def load_weights():
    """Loads weights from the JSON file."""
    if not os.path.exists(WEIGHTS_FILE):
        print(f"Warning: '{WEIGHTS_FILE}' not found. Using default weights.")
        # Default weights optimized for line clearing
        return {
            "weight_height": -0.5,
            "weight_line_completed": 1.0,
            "weight_holes": -0.8,
            "weight_bumpiness": -0.4,
            "weight_max_height": -0.6,
            "weight_wells": -0.4,
        }
    with open(WEIGHTS_FILE, 'r') as f:
        return json.load(f)

WEIGHTS = load_weights()
print(f"[DEBUG] Loaded AI weights: {WEIGHTS}")

# ==============================================================================
#  Evaluation Functions (now imported from game_logic)
# ==============================================================================

def evaluate_board_basic(board: List[List[int]], lines_cleared: int) -> float:
    """
    基础评分函数，用于移动评估
    """
    height_sum = sum(get_col_heights(board))
    holes = count_holes(board)
    bumpiness = calculate_bumpiness(board)
    max_height = get_max_height(board)
    wells = get_wells_depth(board)
    
    score = (
        WEIGHTS.get("weight_height", 0) * height_sum +
        WEIGHTS.get("weight_holes", 0) * holes +
        WEIGHTS.get("weight_bumpiness", 0) * bumpiness +
        WEIGHTS.get("weight_line_completed", 0) * lines_cleared +
        WEIGHTS.get("weight_max_height", 0) * max_height +
        WEIGHTS.get("weight_wells", 0) * wells
    )
    
    return score

def evaluate_board_enhanced(board: List[List[int]], lines_cleared: int, estimated_score: int = 0) -> float:
    """
    增强评分函数，与训练时的enhanced_fitness保持一致
    """
    # 基础评分
    base_score = evaluate_board_basic(board, lines_cleared)
    
    # 增强奖励 - 消行能力
    lines_bonus = 0
    if lines_cleared > 0:
        # 消行奖励，与训练时保持一致
        TARGET_LINES = 1000
        LINES_REWARD_FACTOR = 10
        lines_bonus = lines_cleared * LINES_REWARD_FACTOR * (1 + lines_cleared / TARGET_LINES)
        
        # 多行消除额外奖励
        if lines_cleared >= 4:  # 四行消除
            lines_bonus *= 1.5
        elif lines_cleared >= 3:  # 三行消除
            lines_bonus *= 1.2
    
    # 避免过高的惩罚
    max_height = get_max_height(board)
    if max_height > 15:  # 接近游戏结束
        base_score -= (max_height - 15) * 100  # 强烈惩罚过高
    
    return base_score + lines_bonus

# ==============================================================================
#  Genetic Algorithm Move Selection (Using the Shared Physics Engine)
# ==============================================================================

def get_all_possible_moves(board: List[List[int]], piece_name: str) -> List[Dict]:
    """
    使用逐步执行模拟来找到所有可能的移动
    这与前端的实际执行过程完全一致
    """
    possible_moves = []
    piece_shape = PIECE_SHAPES[piece_name]
    start_x, start_y = get_piece_start_position(piece_shape)
    
    print(f"[DEBUG] Searching moves for piece {piece_name}, start position: ({start_x}, {start_y})")
    
    # 搜索所有可能的旋转和位置组合
    for rotation_count in range(4):
        # 搜索范围基于游戏区域宽度
        for target_x in range(-3, GRID_WIDTH + 3):  # 扩大搜索范围以确保不遗漏
            
            final_board, lines_cleared = simulate_step_by_step_execution(
                board, piece_shape, rotation_count, target_x
            )
            
            if final_board is not None:
                possible_moves.append({
                    "rotation": rotation_count,
                    "x": target_x,
                    "board_state": final_board,
                    "lines_cleared": lines_cleared
                })

    print(f"[DEBUG] Found {len(possible_moves)} possible moves for piece {piece_name}")
    return possible_moves

def get_best_move_with_genetic_agent(board: List[List[int]], current_piece_name: str) -> Dict:
    """
    使用遗传算法权重选择最佳移动
    现在使用增强评分函数，与训练时保持一致
    """
    print(f"[DEBUG] Getting best move for piece: {current_piece_name}")
    
    best_score = float('-inf')
    best_move = None

    possible_moves = get_all_possible_moves(board, current_piece_name)

    if not possible_moves:
        print("[WARNING] No possible moves found, returning default")
        return {"x": 5, "rotation": 0}

    for i, move in enumerate(possible_moves):
        # 使用增强评分函数
        score = evaluate_board_enhanced(move["board_state"], move["lines_cleared"])

        if score > best_score:
            best_score = score
            best_move = {
                "x": move["x"],
                "rotation": move["rotation"],
            }
            
        # 打印前几个候选移动的详细信息
        if i < 5:
            print(f"[DEBUG] Move {i+1}: x={move['x']}, rot={move['rotation']}, score={score:.3f}, lines={move['lines_cleared']}")
            
    if best_move is None:
        print("[ERROR] No best move found, returning default")
        return {"x": 5, "rotation": 0}
        
    print(f"[DEBUG] Best move selected: x={best_move['x']}, rotation={best_move['rotation']}, score={best_score:.3f}")
    return best_move