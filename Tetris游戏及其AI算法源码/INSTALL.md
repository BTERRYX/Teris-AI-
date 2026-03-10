# 俄罗斯方块AI项目安装指南

## 🚀 快速开始

### 1. 环境要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10/11, macOS, Linux
- **内存**: 最少4GB RAM (推荐8GB+)
- **数据库**: Oracle Database (可选，用于用户系统)

### 2. 安装依赖

#### 方法一：完整安装 (推荐)
```bash
pip install -r requirements.txt
```

#### 方法二：最小安装 (仅AI功能)
```bash
pip install -r requirements-core.txt
```

#### 方法三：手动安装核心包
```bash
pip install Flask==2.3.3 Flask-CORS==4.0.0 websockets==11.0.3 numpy==1.24.3
```

### 3. 数据库配置 (可选)

如果需要用户登录和排行榜功能：

#### 安装Oracle数据库
1. 下载并安装Oracle Database Express Edition
2. 创建数据库表：
```sql
-- 用户表
CREATE TABLE TETRIS_USERS (
    ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    USERNAME VARCHAR2(50) UNIQUE NOT NULL,
    PASSWORD VARCHAR2(100) NOT NULL,
    CREATED_DATE DATE DEFAULT SYSDATE
);

-- 分数表
CREATE TABLE TETRIS_SCORES (
    ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    USER_ID NUMBER REFERENCES TETRIS_USERS(ID),
    SCORE NUMBER NOT NULL,
    CREATED_DATE DATE DEFAULT SYSDATE
);
```

#### 修改数据库连接配置
编辑 `app.py` 中的数据库连接参数：
```python
def get_db_connection():
    return cx_Oracle.connect(
        user="你的用户名",
        password="你的密码", 
        dsn="localhost:1521/orcl"
    )
```

### 4. 启动服务

#### 启动AI服务器
```bash
python ai_server.py
```
服务器将在 `ws://localhost:8888` 启动

#### 启动Web应用
```bash
python app.py
```
Web应用将在 `http://localhost:5000` 启动

#### 一键重启服务 (训练后)
```bash
python restart_services.py
```

### 5. 访问游戏

打开浏览器访问：
- **游戏页面**: http://localhost:5000
- **排行榜**: http://localhost:5000/leaderboard_page

## 🧬 AI训练

### 开始训练
```bash
python train_ga.py
```

### 训练参数调整
编辑 `train_ga.py` 中的配置：
```python
POPULATION_SIZE = 50      # 种群大小
TARGET_LINES = 1000       # 目标消行数
MUTATION_RATE = 0.15      # 变异率
MAX_PIECES = 10000        # 每局最大方块数
```

### 模型管理
- `best_genetic_agent.json` - 当前最佳模型
- `best_lines_agent_XXXX.json` - 高分模型备份

## 🔧 故障排除

### 常见问题

#### 1. 端口占用
```bash
# 检查端口使用情况
netstat -ano | findstr :5000
netstat -ano | findstr :8888

# 杀死占用进程 (Windows)
taskkill /PID <进程ID> /F
```

#### 2. 依赖安装失败
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### 3. Oracle数据库连接失败
- 检查Oracle服务是否启动
- 确认连接参数正确
- 如不需要用户系统，可跳过数据库配置

#### 4. WebSocket连接失败
- 确认AI服务器已启动 (ai_server.py)
- 检查防火墙设置
- 确认端口8888未被占用

### 性能优化

#### 1. 训练加速
```python
# 在train_ga.py中调整参数
MAX_PIECES = 5000         # 减少单局方块数
POPULATION_SIZE = 30      # 减少种群大小
```

#### 2. 内存优化
- 关闭不必要的程序
- 监控内存使用: `python -c "import psutil; print(f'内存使用: {psutil.virtual_memory().percent}%')"`

## 📁 文件结构说明

```
方块new/
├── requirements.txt           # 完整依赖列表
├── requirements-core.txt      # 核心依赖列表  
├── INSTALL.md                # 本安装指南
├── README.md                 # 项目技术文档
├── app.py                    # Web应用主程序
├── ai_server.py              # AI WebSocket服务器
├── train_ga.py               # 遗传算法训练程序
├── game_logic.py             # 游戏逻辑统一模块
├── simple_heuristic_ai.py    # AI决策算法
├── restart_services.py       # 服务管理工具
├── best_*.json               # 训练好的AI模型
├── index.html                # 游戏主页面
├── leaderboard.html          # 排行榜页面
├── login_register.html       # 登录注册页面
└── static/
    └── tetris.js             # 前端游戏逻辑
```

## 🎯 使用建议

1. **首次使用**: 先运行核心AI功能，确认正常后再配置数据库
2. **开发调试**: 使用 `python -u` 参数查看实时输出
3. **生产部署**: 考虑使用gunicorn等WSGI服务器
4. **模型备份**: 定期备份训练好的模型文件

## 📞 技术支持

如遇到问题，请检查：
1. Python版本是否兼容
2. 依赖包是否正确安装
3. 端口是否被占用
4. 防火墙设置是否正确

更多技术细节请参考 `README.md` 文档。 