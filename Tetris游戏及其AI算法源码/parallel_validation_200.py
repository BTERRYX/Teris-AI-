#!/usr/bin/env python3
"""
并行化大规模验证脚本
测试stable模型在200局游戏中的平均消行表现
"""

import json
import random
import time
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from game_logic import (
    GRID_WIDTH, GRID_HEIGHT, PIECE_SHAPES, simulate_step_by_step_execution,
    get_col_heights, count_holes, calculate_bumpiness, get_max_height, get_wells_depth,
    get_piece_start_position, check_collision
)

class LargeScaleGame:
    """大规模测试游戏实例"""
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.lines_cleared = 0
        self.game_over = False
        self.pieces_placed = 0
        self.current_piece_name = self.new_piece_name()
        self.current_piece_shape = PIECE_SHAPES[self.current_piece_name]
        
    def new_piece_name(self):
        return random.choice(list(PIECE_SHAPES.keys()))
    
    def step(self, move):
        if self.game_over or self.pieces_placed >= 8000:
            self.game_over = True
            return

        board_after_move, lines = simulate_step_by_step_execution(
            self.board, self.current_piece_shape, move['rotation'], move['x']
        )
        
        if board_after_move is None:
            self.game_over = True
            return

        self.board = board_after_move
        self.lines_cleared += lines
        self.pieces_placed += 1
        
        self.current_piece_name = self.new_piece_name()
        self.current_piece_shape = PIECE_SHAPES[self.current_piece_name]
        
        start_x, start_y = get_piece_start_position(self.current_piece_shape)
        if check_collision(self.board, self.current_piece_shape, start_x, start_y):
            self.game_over = True

class LargeScaleAgent:
    """大规模测试智能体"""
    def __init__(self, weights):
        self.weights = weights
    
    def get_fitness(self, board, lines_cleared):
        score = (
            self.weights["weight_height"] * sum(get_col_heights(board)) +
            self.weights["weight_holes"] * count_holes(board) +
            self.weights["weight_bumpiness"] * calculate_bumpiness(board) +
            self.weights["weight_line_completed"] * lines_cleared +
            self.weights["weight_max_height"] * get_max_height(board) +
            self.weights["weight_wells"] * get_wells_depth(board)
        )
        return score
    
    def find_best_move(self, game):
        best_score = float('-inf')
        best_move = None
        
        for rotation_count in range(4):
            for target_x in range(-3, GRID_WIDTH + 3):
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

def run_single_parallel_game(test_data):
    """运行单个并行游戏"""
    weights, seed, game_id = test_data
    
    agent = LargeScaleAgent(weights)
    game = LargeScaleGame(seed=seed)
    
    start_time = time.time()
    moves = 0
    timeout_limit = 15000
    
    while not game.game_over and moves < timeout_limit:
        move = agent.find_best_move(game)
        game.step(move)
        moves += 1
        
        if time.time() - start_time > 180:  # 3分钟超时
            break
    
    elapsed_time = time.time() - start_time
    efficiency = game.lines_cleared / max(1, game.pieces_placed)
    
    return {
        'game_id': game_id,
        'seed': seed,
        'lines_cleared': game.lines_cleared,
        'pieces_placed': game.pieces_placed,
        'elapsed_time': elapsed_time,
        'efficiency': efficiency,
        'timeout': moves >= timeout_limit or elapsed_time >= 180
    }

def analyze_large_scale_results(results):
    """分析大规模测试结果"""
    successful_games = [r for r in results if not r['timeout']]
    
    if not successful_games:
        return None
    
    lines_list = [r['lines_cleared'] for r in successful_games]
    efficiency_list = [r['efficiency'] for r in successful_games]
    time_list = [r['elapsed_time'] for r in successful_games]
    
    analysis = {
        'total_games': len(results),
        'successful_games': len(successful_games),
        'timeout_count': len([r for r in results if r['timeout']]),
        'success_rate': len(successful_games) / len(results) * 100,
        'lines_stats': {
            'mean': statistics.mean(lines_list),
            'median': statistics.median(lines_list),
            'stdev': statistics.stdev(lines_list) if len(lines_list) > 1 else 0,
            'min': min(lines_list),
            'max': max(lines_list),
            'q1': statistics.quantiles(lines_list, n=4)[0] if len(lines_list) >= 4 else 0,
            'q3': statistics.quantiles(lines_list, n=4)[2] if len(lines_list) >= 4 else 0
        },
        'efficiency_stats': {
            'mean': statistics.mean(efficiency_list),
            'stdev': statistics.stdev(efficiency_list) if len(efficiency_list) > 1 else 0
        },
        'time_stats': {
            'mean': statistics.mean(time_list),
            'total': sum(time_list)
        },
        'achievement_rates': {
            '500+': sum(1 for x in lines_list if x >= 500) / len(lines_list) * 100,
            '1000+': sum(1 for x in lines_list if x >= 1000) / len(lines_list) * 100,
            '1500+': sum(1 for x in lines_list if x >= 1500) / len(lines_list) * 100,
            '2000+': sum(1 for x in lines_list if x >= 2000) / len(lines_list) * 100,
            '2500+': sum(1 for x in lines_list if x >= 2500) / len(lines_list) * 100,
            '3000+': sum(1 for x in lines_list if x >= 3000) / len(lines_list) * 100,
            '3500+': sum(1 for x in lines_list if x >= 3500) / len(lines_list) * 100,
            '4000+': sum(1 for x in lines_list if x >= 4000) / len(lines_list) * 100
        }
    }
    
    # 稳定性系数
    analysis['stability_coefficient'] = analysis['lines_stats']['stdev'] / analysis['lines_stats']['mean'] if analysis['lines_stats']['mean'] > 0 else float('inf')
    
    return analysis

def print_progress_bar(current, total, start_time):
    """打印进度条"""
    percent = current / total * 100
    elapsed = time.time() - start_time
    eta = (elapsed / current * (total - current)) if current > 0 else 0
    
    bar_length = 40
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    print(f'\r进度: |{bar}| {current}/{total} ({percent:.1f}%) '
          f'已用时: {elapsed:.1f}s 预计剩余: {eta:.1f}s', end='', flush=True)

def main():
    """主测试函数"""
    print("🚀 并行化大规模验证 - 200局游戏测试")
    print("=" * 60)
    
    # 加载stable模型
    model_file = "best_genetic_agent.json"
    try:
        with open(model_file, 'r') as f:
            weights = json.load(f)
        print(f"✅ 已加载模型: {model_file}")
        
        # 验证是否为stable权重
        if abs(weights.get("weight_holes", 0) + 1.62) < 0.01:
            print(f"✅ 确认为stable模型权重")
        else:
            print(f"⚠️  权重可能不是stable模型")
            
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return
    
    # 测试配置
    total_games = 200
    max_workers = 12  # 并行进程数
    
    print(f"\n🎯 测试配置:")
    print(f"   总游戏数: {total_games}")
    print(f"   并行进程: {max_workers}")
    print(f"   预计时间: {total_games * 15 / max_workers / 60:.1f} 分钟")
    
    # 生成测试数据
    test_data = []
    random.seed(42)  # 固定随机种子确保可复现
    for game_id in range(total_games):
        seed = random.randint(1, 1000000)
        test_data.append((weights, seed, game_id))
    
    print(f"\n🚀 开始并行测试...")
    start_time = time.time()
    
    # 并行执行测试
    results = []
    completed_count = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_game = {executor.submit(run_single_parallel_game, data): data[2] 
                         for data in test_data}
        
        # 收集结果并显示进度
        for future in as_completed(future_to_game):
            game_id = future_to_game[future]
            try:
                result = future.result()
                results.append(result)
                completed_count += 1
                
                # 更新进度条
                print_progress_bar(completed_count, total_games, start_time)
                
                # 每50局显示一次中间统计
                if completed_count % 50 == 0:
                    temp_successful = [r for r in results if not r['timeout']]
                    if temp_successful:
                        temp_avg = statistics.mean([r['lines_cleared'] for r in temp_successful])
                        print(f"\n   中间统计 ({completed_count}局): 平均 {temp_avg:.1f} 行, 成功率 {len(temp_successful)/len(results)*100:.1f}%")
                    
            except Exception as e:
                print(f"\n❌ 游戏 {game_id} 执行失败: {e}")
                completed_count += 1
                print_progress_bar(completed_count, total_games, start_time)
    
    total_time = time.time() - start_time
    print(f"\n\n⏱️  总测试时间: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    
    # 分析结果
    analysis = analyze_large_scale_results(results)
    
    if not analysis:
        print("❌ 没有成功的游戏，无法分析")
        return
    
    # 输出详细分析
    print(f"\n📊 大规模测试结果分析")
    print("=" * 60)
    
    print(f"📈 基本统计:")
    print(f"   总游戏数: {analysis['total_games']}")
    print(f"   成功游戏: {analysis['successful_games']}")
    print(f"   超时游戏: {analysis['timeout_count']}")
    print(f"   成功率: {analysis['success_rate']:.1f}%")
    
    lines_stats = analysis['lines_stats']
    print(f"\n🎯 消行表现:")
    print(f"   平均消行: {lines_stats['mean']:.1f} 行")
    print(f"   中位数: {lines_stats['median']:.1f} 行")
    print(f"   标准差: {lines_stats['stdev']:.1f} 行")
    print(f"   最小值: {lines_stats['min']} 行")
    print(f"   最大值: {lines_stats['max']} 行")
    print(f"   第一四分位: {lines_stats['q1']:.1f} 行")
    print(f"   第三四分位: {lines_stats['q3']:.1f} 行")
    print(f"   稳定性系数: {analysis['stability_coefficient']:.3f}")
    
    print(f"\n🏆 目标达成率:")
    for threshold, rate in analysis['achievement_rates'].items():
        print(f"   {threshold:6}: {rate:6.1f}%")
    
    print(f"\n⚡ 性能统计:")
    print(f"   平均游戏时长: {analysis['time_stats']['mean']:.1f} 秒")
    print(f"   平均效率: {analysis['efficiency_stats']['mean']:.4f}")
    
    # 与预期对比
    expected_avg = 1610.5
    actual_vs_expected = (lines_stats['mean'] / expected_avg) * 100
    
    print(f"\n📈 与预期对比:")
    print(f"   预期平均: {expected_avg} 行")
    print(f"   实际平均: {lines_stats['mean']:.1f} 行")
    print(f"   达成率: {actual_vs_expected:.1f}%")
    
    # 性能分级
    if lines_stats['mean'] >= 2000:
        grade = "S+ (卓越)"
    elif lines_stats['mean'] >= 1500:
        grade = "S (优秀)"
    elif lines_stats['mean'] >= 1200:
        grade = "A (良好)"
    elif lines_stats['mean'] >= 1000:
        grade = "B (合格)"
    else:
        grade = "C (需改进)"
    
    print(f"\n🎖️  性能评级: {grade}")
    
    # 稳定性评估
    if analysis['stability_coefficient'] < 0.6:
        stability_grade = "优秀"
    elif analysis['stability_coefficient'] < 0.8:
        stability_grade = "良好"
    elif analysis['stability_coefficient'] < 1.0:
        stability_grade = "中等"
    else:
        stability_grade = "需改进"
    
    print(f"🔒 稳定性评级: {stability_grade}")
    
    # 保存详细结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = f"parallel_validation_200_results_{timestamp}.json"
    
    save_data = {
        'test_config': {
            'total_games': total_games,
            'max_workers': max_workers,
            'test_time': total_time,
            'model_file': model_file
        },
        'results': results,
        'analysis': analysis,
        'timestamp': timestamp
    }
    
    with open(result_file, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n💾 详细结果已保存: {result_file}")
    
    # 最终结论
    print(f"\n✨ 最终结论:")
    if analysis['success_rate'] >= 95 and lines_stats['mean'] >= 1200:
        print(f"   🎉 Stable模型在200局大规模测试中表现优异！")
        print(f"   ✅ 平均消行达到 {lines_stats['mean']:.1f} 行")
        print(f"   ✅ 成功率高达 {analysis['success_rate']:.1f}%")
        print(f"   ✅ 稳定性{stability_grade}")
    elif analysis['success_rate'] >= 90 and lines_stats['mean'] >= 1000:
        print(f"   👍 Stable模型表现良好，符合预期")
    else:
        print(f"   ⚠️  模型表现低于预期，可能需要进一步优化")
    
    print(f"\n🎯 推荐:")
    if lines_stats['mean'] >= 1500:
        print(f"   • 模型已达到生产级别，可以正式部署")
        print(f"   • 建议作为主力AI模型使用")
    else:
        print(f"   • 模型基本可用，建议继续监控")
        print(f"   • 可考虑进一步优化参数")

if __name__ == "__main__":
    main() 