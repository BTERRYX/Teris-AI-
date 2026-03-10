#!/usr/bin/env python3
"""
重启AI服务脚本
在训练完成后使用，自动重启AI服务器使用新的权重
"""

import subprocess
import sys
import time
import os

def check_file_exists(filepath):
    """检查文件是否存在"""
    return os.path.exists(filepath)

def show_current_weights():
    """显示当前权重"""
    try:
        import json
        with open('best_genetic_agent.json', 'r') as f:
            weights = json.load(f)
        print("📊 当前AI权重:")
        for key, value in weights.items():
            print(f"  {key}: {value:.4f}")
        return True
    except Exception as e:
        print(f"❌ 无法读取权重文件: {e}")
        return False

def test_ai_quick():
    """快速测试AI"""
    try:
        print("🧪 快速测试AI...")
        from simple_heuristic_ai import get_best_move_with_genetic_agent
        
        # 创建简单测试棋盘
        board = [[0] * 10 for _ in range(20)]
        # 底部添加一些方块
        for i in range(5):
            board[19][i] = 1
            
        # 测试几个方块
        test_pieces = ['I', 'T', 'O']
        for piece in test_pieces:
            move = get_best_move_with_genetic_agent(board, piece)
            print(f"  {piece}方块决策: x={move['x']}, rotation={move['rotation']}")
        
        print("✅ AI测试通过!")
        return True
    except Exception as e:
        print(f"❌ AI测试失败: {e}")
        return False

def main():
    print("🔄 AI服务重启工具")
    print("=" * 40)
    
    # 检查权重文件
    if not check_file_exists('best_genetic_agent.json'):
        print("❌ 未找到 best_genetic_agent.json 文件")
        print("请先运行训练: python train_ga.py")
        return
    
    # 显示当前权重
    if not show_current_weights():
        return
    
    # 快速测试AI
    if not test_ai_quick():
        print("\n⚠️  AI测试失败，建议检查代码")
        response = input("是否继续重启服务？(y/N): ")
        if response.lower() != 'y':
            return
    
    print("\n🚀 准备重启AI服务...")
    print("请按以下步骤操作：")
    print("1. 如果AI服务器正在运行，请按 Ctrl+C 停止")
    print("2. 重新运行: python ai_server.py")
    print("3. 重新运行: python app.py")
    print("4. 在浏览器中测试AI模式")
    
    print("\n📝 建议测试内容：")
    print("- 观察AI是否能消除更多行")
    print("- 检查AI决策是否更稳定")
    print("- 对比训练前后的表现")
    
    # 检查是否有高消行智能体文件
    high_lines_files = [f for f in os.listdir('.') if f.startswith('best_lines_agent_')]
    if high_lines_files:
        print(f"\n🎉 发现 {len(high_lines_files)} 个高消行智能体文件:")
        for file in sorted(high_lines_files):
            lines = file.replace('best_lines_agent_', '').replace('.json', '')
            print(f"  - {file} (消行: {lines})")
        
        print("\n💡 提示: 您可以手动替换 best_genetic_agent.json 来测试不同的智能体")

if __name__ == "__main__":
    main() 