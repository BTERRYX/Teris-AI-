from flask import Flask, request, jsonify, send_file
import cx_Oracle
from flask_cors import CORS

app = Flask(
    __name__, 
    static_url_path='/static',  # 浏览器访问静态文件的前缀（如 /static/tetris.js）
    static_folder='static'     # 本地静态文件目录名（必须与实际文件夹名一致）
)
CORS(app)

# 数据库连接配置
def get_db_connection():
    dsn = cx_Oracle.makedsn(
        host="localhost",
        port=1521,
        sid="orcl"
    )
    return cx_Oracle.connect(
        user="system",
        password="123456",
        dsn="localhost:1521/orcl"
    )

# 用户注册
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "用户名和密码不能为空"}), 400

    conn = None
    cursor = None  # 提前声明变量
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO TETRIS_USERS (USERNAME, PASSWORD) VALUES (:1, :2)", (username, password))
        conn.commit()
        return jsonify({"message": "注册成功"}), 201
    except cx_Oracle.IntegrityError as e:
        error, = e.args
        if error.code == 1:  # ORA-00001: unique constraint violated
            return jsonify({"message": "用户名已存在"}), 409
        else:
            return jsonify({"message": f"数据库错误: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"错误: {str(e)}"}), 500
    finally:
        # 关闭资源前检查变量是否已定义
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 用户登录
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "用户名和密码不能为空"}), 400

    conn = None
    cursor = None  # 提前声明变量
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT ID FROM TETRIS_USERS WHERE USERNAME = :1 AND PASSWORD = :2", (username, password))
        user = cursor.fetchone()

        if user:
            return jsonify({"message": "登录成功", "user_id": user[0]}), 200
        else:
            return jsonify({"message": "用户名或密码错误"}), 401
    except Exception as e:
        return jsonify({"message": f"错误: {str(e)}"}), 500
    finally:
        # 关闭资源前检查变量是否已定义
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 获取排行榜
@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    conn = None
    cursor = None  # 提前声明变量
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 替换为修改后的 SQL
        cursor.execute("""
        SELECT USERNAME, SCORE
        FROM (
            SELECT U.USERNAME, S.SCORE 
            FROM TETRIS_SCORES S 
            JOIN TETRIS_USERS U ON S.USER_ID = U.ID 
            ORDER BY S.SCORE DESC 
        )
        WHERE ROWNUM <= 10
        """)  # 注意去掉了原 SQL 末尾的分号
        leaderboard_data = cursor.fetchall()
        result = [{"username": row[0], "score": row[1]} for row in leaderboard_data]
        return jsonify({"leaderboard": result}), 200
    except Exception as e:
        # 打印详细错误
        print(f"数据库查询错误: {str(e)}")  
        return jsonify({"message": f"错误: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 提供登录注册界面
@app.route('/')
def login_register():
    return send_file('login_register.html')

@app.route('/update_score', methods=['POST'])
def update_score():
    data = request.get_json()
    user_id = data.get('user_id')
    score = data.get('score')

    if not user_id or not score:
        return jsonify({"message": "用户ID和分数不能为空"}), 400

    conn = None
    cursor = None  # 提前声明变量
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查用户是否已有分数记录
        cursor.execute("SELECT SCORE FROM TETRIS_SCORES WHERE USER_ID = :1", (user_id,))
        existing_score = cursor.fetchone()

        if existing_score:
            if score > existing_score[0]:
                # 更新分数
                cursor.execute("UPDATE TETRIS_SCORES SET SCORE = :1 WHERE USER_ID = :2", (score, user_id))
                conn.commit()
                return jsonify({"message": "分数已更新"}), 200
            else:
                return jsonify({"message": "新分数不高于现有分数，未更新"}), 200
        else:
            # 插入新分数记录
            cursor.execute("INSERT INTO TETRIS_SCORES (USER_ID, SCORE) VALUES (:1, :2)", (user_id, score))
            conn.commit()
            return jsonify({"message": "分数已插入"}), 201
    except Exception as e:
        return jsonify({"message": f"错误: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/user/<int:user_id>/stats', methods=['GET'])
def user_stats(user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取用户的排名
        cursor.execute("""
            SELECT RANK
            FROM (
                SELECT U.ID, ROW_NUMBER() OVER (ORDER BY S.SCORE DESC) AS RANK
                FROM TETRIS_USERS U
                JOIN TETRIS_SCORES S ON U.ID = S.USER_ID
            )
            WHERE ID = :1
        """, (user_id,))
        rank = cursor.fetchone()

        if rank:
            rank = rank[0]
        else:
            rank = None

        # 获取用户的分数
        cursor.execute("SELECT MAX(SCORE) FROM TETRIS_SCORES WHERE USER_ID = :1", (user_id,))
        high_score = cursor.fetchone()[0]
        user_title = "草民"
        if rank == 1:
            user_title = "皇帝"

        return jsonify({
            "rank": rank,
            "high_score": high_score,
            "title": user_title
        }), 200
    except Exception as e:
        return jsonify({"message": f"错误: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# 提供排行榜界面
@app.route('/leaderboard_page')  # 避免与获取排行榜数据的接口路由冲突，修改路由名
def show_leaderboard():
    return send_file('leaderboard.html')

#提供游戏界面
@app.route('/index')
def show_tetris():
    return send_file('index.html')


if __name__ == '__main__':
     app.run(debug=True, host='0.0.0.0')