import asyncio
import websockets
import json
from simple_heuristic_ai import get_best_move_with_genetic_agent
from game_logic import PIECE_TYPE_MAP

def get_piece_name_from_shape(shape_from_frontend: list) -> str:
    """
    从前端发送的方块形状识别方块类型
    使用更robust的方法，检查非零值来确定方块类型
    """
    piece_id = 0
    for row in shape_from_frontend:
        for cell in row:
            if cell != 0:
                piece_id = cell
                break
        if piece_id != 0:
            break
            
    if piece_id == 0:
        print("Error: Empty piece shape received")
        return None

    # 使用映射表获取方块名称
    piece_name = PIECE_TYPE_MAP.get(piece_id)
    if piece_name is None:
        print(f"Error: Unknown piece ID {piece_id}")
        return None
        
    return piece_name

def validate_game_state(data):
    """验证从前端接收的游戏状态数据"""
    required_fields = ['board', 'piece']
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    if 'shape' not in data['piece']:
        return False, "Missing piece shape"
    
    board = data['board']
    if len(board) != 20 or any(len(row) != 10 for row in board):
        return False, "Invalid board dimensions"
    
    return True, "Valid"

async def handler(websocket, path):
    print(f"New AI connection established")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f"[DEBUG] Received data type: {data.get('type')}")
                
                if data.get("type") == "state":
                    # 验证游戏状态
                    is_valid, error_msg = validate_game_state(data)
                    if not is_valid:
                        print(f"[ERROR] Invalid game state: {error_msg}")
                        continue
                    
                    board = data["board"]
                    current_piece_shape = data["piece"]["shape"]
                    
                    print(f"[DEBUG] Board height: {len(board)}, width: {len(board[0]) if board else 0}")
                    print(f"[DEBUG] Piece shape: {current_piece_shape}")

                    # 识别方块类型
                    current_piece_name = get_piece_name_from_shape(current_piece_shape)
                    
                    if not current_piece_name:
                        print(f"[ERROR] Could not identify piece for shape {current_piece_shape}")
                        # 发送默认响应，避免前端卡住
                        response_data = {
                            "type": "move",
                            "targetX": 5,  # 中间位置
                            "rotation": 0
                        }
                        await websocket.send(json.dumps(response_data))
                        continue

                    print(f"[DEBUG] Identified piece: {current_piece_name}")
                    
                    # 获取AI决策
                    best_action = get_best_move_with_genetic_agent(board, current_piece_name)
                    
                    print(f"[DEBUG] AI decision: x={best_action['x']}, rotation={best_action['rotation']}")
                    
                    # 发送响应
                    response_data = {
                        "type": "move",
                        "targetX": best_action['x'],
                        "rotation": best_action['rotation']
                    }
                    
                    await websocket.send(json.dumps(response_data))
                    print(f"[DEBUG] Sent AI response: {response_data}")
                    
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON decode error: {e}")
            except Exception as e:
                print(f"[ERROR] Error processing message: {e}")
                
    except websockets.exceptions.ConnectionClosedOK:
        print("AI connection closed normally")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"AI connection closed with error: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error in AI connection: {e}")

async def main():
    print("Starting AI Server...")
    start_server = await websockets.serve(handler, "localhost", 8888)
    print("AI WebSocket server listening on ws://localhost:8888")
    print("Waiting for connections...")
    await start_server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())