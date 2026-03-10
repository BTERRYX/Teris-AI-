from typing import List, Dict, Tuple

# ==============================================================================
#  SHARED CONSTANTS AND DEFINITIONS
# ==============================================================================

GRID_HEIGHT = 10
GRID_WIDTH = 10

# 方块形状定义 - 与前端tetris.js完全一致
PIECE_SHAPES = {
    'I': [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    'J': [[2, 0, 0], [2, 2, 2], [0, 0, 0]],
    'L': [[0, 0, 3], [3, 3, 3], [0, 0, 0]],
    'O': [[0, 4, 4], [0, 4, 4], [0, 0, 0]],
    'S': [[0, 5, 5], [5, 5, 0], [0, 0, 0]],
    'T': [[0, 6, 0], [6, 6, 6], [0, 0, 0]],
    'Z': [[7, 7, 0], [0, 7, 7], [0, 0, 0]]
}

# 方块类型映射（用于识别前端发送的方块）
PIECE_TYPE_MAP = {
    1: 'I', 2: 'J', 3: 'L', 4: 'O', 5: 'S', 6: 'T', 7: 'Z'
}

# ==============================================================================
#  CORE PHYSICS AND SIMULATION (Single Source of Truth)
# ==============================================================================

def rotate_piece(piece: List[List[int]]) -> List[List[int]]:
    """Rotates a piece clockwise."""
    return [list(row) for row in zip(*piece[::-1])]

def get_piece_rotations(piece_shape: List[List[int]]) -> List[List[List[int]]]:
    """Helper to generate all 4 rotations for PIECE_ROTATIONS dict."""
    rotations = [piece_shape]
    current_piece = piece_shape
    for _ in range(3):
        current_piece = rotate_piece(current_piece)
        if not any(all(row_a == row_b for row_a, row_b in zip(current_piece, r)) for r in rotations):
            rotations.append(current_piece)
    return rotations

# We must define PIECE_ROTATIONS *after* its dependency, get_piece_rotations, is defined.
PIECE_ROTATIONS = {name: get_piece_rotations(shape) for name, shape in PIECE_SHAPES.items()}

def check_collision(board: List[List[int]], piece: List[List[int]], x: int, y: int) -> bool:
    """Checks for collision."""
    for i in range(len(piece)):
        for j in range(len(piece[0])):
            if piece[i][j] != 0:
                if (
                    x + j < 0 
                    or x + j >= GRID_WIDTH 
                    or y + i >= GRID_HEIGHT 
                    or (y + i >= 0 and board[y + i][x + j] != 0)
                ):
                    return True
    return False

def find_drop_height(board: List[List[int]], piece: List[List[int]], x: int) -> int:
    """Finds the final drop height for a piece."""
    y = 0
    while not check_collision(board, piece, x, y + 1):
        y += 1
    return y

def place_piece(board: List[List[int]], piece: List[List[int]], x: int, y: int) -> List[List[int]]:
    """Places a piece on the board."""
    new_board = [row[:] for row in board]
    for i in range(len(piece)):
        for j in range(len(piece[0])):
            if piece[i][j] != 0 and y + i >= 0:
                new_board[y + i][x + j] = piece[i][j]
    return new_board

def remove_complete_lines(board: List[List[int]]) -> Tuple[List[List[int]], int]:
    """Removes complete lines and returns the new board and lines cleared."""
    new_board = [row for row in board if not all(cell != 0 for cell in row)]
    lines_cleared = len(board) - len(new_board)
    
    while len(new_board) < GRID_HEIGHT:
        new_board.insert(0, [0] * GRID_WIDTH)
    
    return new_board, lines_cleared

def get_piece_start_position(piece_shape: List[List[int]]) -> Tuple[int, int]:
    """获取方块的起始位置，与前端逻辑完全一致"""
    start_x = (GRID_WIDTH // 2) - (len(piece_shape[0]) // 2)
    start_y = 0
    return start_x, start_y

def _apply_one_rotation_with_kick(board, current_shape, current_x, current_y):
    """
    Simulates a single press of the 'rotate' button, replicating frontend wall kicks EXACTLY.
    Returns (new_shape, new_x, new_y) or (None, None, None) if rotation is impossible.
    """
    rotated_shape = rotate_piece(current_shape)

    # Base case: no collision
    if not check_collision(board, rotated_shape, current_x, current_y):
        return rotated_shape, current_x, current_y

    # Test kicks in the exact same order as tetris.js
    kick_tests = [
        (current_x + 1, current_y),     # Kick right 1
        (current_x - 1, current_y),     # Kick left 1
        (current_x, current_y - 1),     # Kick up 1 (for I-piece vertical spawn)
        (current_x + 2, current_y),     # Kick right 2 (for I-piece)
        (current_x - 2, current_y)      # Kick left 2 (for I-piece)
    ]

    for test_x, test_y in kick_tests:
        if not check_collision(board, rotated_shape, test_x, test_y):
            return rotated_shape, test_x, test_y
            
    # If all kicks fail
    return None, None, None

def simulate_step_by_step_execution(board, piece_shape, rotation_count, target_x):
    """
    模拟前端逐步执行的过程：先旋转，再移动，最后下落
    这样可以更准确地预测AI指令的实际执行结果
    """
    start_x, start_y = get_piece_start_position(piece_shape)
    
    current_shape = piece_shape
    current_x = start_x
    current_y = start_y
    
    # 逐步旋转，就像前端那样
    for _ in range(rotation_count):
        new_shape, new_x, new_y = _apply_one_rotation_with_kick(board, current_shape, current_x, current_y)
        if new_shape is None:
            return None, 0  # 旋转失败
        current_shape = new_shape
        current_x = new_x
        current_y = new_y
    
    # 逐步水平移动到目标位置
    move_dir = 1 if target_x > current_x else -1
    while current_x != target_x:
        next_x = current_x + move_dir
        if check_collision(board, current_shape, next_x, current_y):
            # 移动失败，无法到达目标位置
            return None, 0
        current_x = next_x
    
    # 下落到底部
    final_y = find_drop_height(board, current_shape, current_x)
    final_board = place_piece(board, current_shape, current_x, final_y)
    
    final_board, lines_cleared = remove_complete_lines(final_board)
    
    return final_board, lines_cleared

def get_final_board_state(board, piece_shape, rotation_count, target_x):
    """
    使用新的逐步执行模拟来获取最终状态
    """
    return simulate_step_by_step_execution(board, piece_shape, rotation_count, target_x)

# ==============================================================================
#  BOARD EVALUATION HELPERS
# ==============================================================================

def get_col_heights(board: List[List[int]]) -> List[int]:
    """Gets the height of each column."""
    heights = [0] * GRID_WIDTH
    for col in range(GRID_WIDTH):
        for row in range(GRID_HEIGHT):
            if board[row][col] != 0:
                heights[col] = GRID_HEIGHT - row
                break
    return heights

def count_holes(board: List[List[int]]) -> int:
    """Calculates the number of holes."""
    holes = 0
    for col in range(GRID_WIDTH):
        block_found = False
        for row in range(GRID_HEIGHT):
            if board[row][col] != 0:
                block_found = True
            elif block_found:
                holes += 1
    return holes

def calculate_bumpiness(board: List[List[int]]) -> float:
    """Calculates the board's bumpiness."""
    heights = get_col_heights(board)
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))

def get_max_height(board: List[List[int]]) -> int:
    """Gets the height of the tallest column."""
    heights = get_col_heights(board)
    return max(heights) if heights else 0

def get_wells_depth(board: List[List[int]]) -> int:
    """Calculates the sum of the depths of all wells."""
    heights = get_col_heights(board)
    wells_depth = 0
    for i in range(len(heights)):
        left_height = heights[i-1] if i > 0 else GRID_HEIGHT
        right_height = heights[i+1] if i < len(heights) - 1 else GRID_HEIGHT
        well_depth = min(left_height, right_height) - heights[i]
        if well_depth > 0:
            wells_depth += well_depth
    return wells_depth 