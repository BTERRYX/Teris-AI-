// 封装初始化函数
function initTetris() {
    // 获取DOM元素
    const canvas = document.getElementById('tetris');
    const ctx = canvas.getContext('2d');
    const scoreElement = document.getElementById('score');
    const linesElement = document.getElementById('lines');
    const levelElement = document.getElementById('level');
    const speedElement = document.getElementById('speed');
    const startButton = document.getElementById('start-button');
    const pauseButton = document.getElementById('pause-button');
    const restartButton = document.getElementById('restart-button');
    const humanModeButton = document.getElementById('human-mode');
    const aiModeButton = document.getElementById('ai-mode');
    const modeToggle = document.getElementById('mode-toggle');
    const toggleDot = document.getElementById('toggle-dot');
    const connectionStatus = document.getElementById('connection-status');
    const aiStatus = document.getElementById('ai-status');

    // 设置画布尺寸
    const COLS = 10;
    const ROWS = 20;
    const BLOCK_SIZE = 30;
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;

    // 方块颜色
    const COLORS = [
        'none',
        '#3B82F6', // I
        '#10B981', // J
        '#F59E0B', // L
        '#EF4444', // O
        '#8B5CF6', // S
        '#EC4899', // T
        '#06B6D4'  // Z
    ];

    // 方块形状
    const SHAPES = [
        [],
        [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]], // I
        [[2, 0, 0], [2, 2, 2], [0, 0, 0]],                         // J
        [[0, 0, 3], [3, 3, 3], [0, 0, 0]],                         // L
        [[0, 4, 4], [0, 4, 4], [0, 0, 0]],                         // O
        [[0, 5, 5], [5, 5, 0], [0, 0, 0]],                         // S
        [[0, 6, 0], [6, 6, 6], [0, 0, 0]],                         // T
        [[7, 7, 0], [0, 7, 7], [0, 0, 0]]                          // Z
    ];

    // 游戏状态
    let board = Array(ROWS).fill().map(() => Array(COLS).fill(0));
    let score = 0;
    let lines = 0;
    let level = 1;
    let dropInterval = 1000; // 初始下落速度（毫秒）
    let dropCounter = 0;
    let lastTime = 0;
    let gameOver = false;
    let isPaused = false;
    let isAiMode = false;
    let isAiConnected = false;

    // 当前方块和下一个方块
    let currentPiece = null;
    let nextPiece = null;
    let isAiThinking = false;
    let socket;

    // 连接 AI 服务器
    function connectToAiServer() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            console.log('[DEBUG] 已连接到 AI 服务器，无需重复连接');
            return;
        }

        socket = new WebSocket('ws://localhost:8888');
        console.log('[DEBUG] 尝试连接 AI 服务器...');
        socket.onerror = () => {
            setTimeout(connectToAiServer, 3000);  // 3秒后重连
        };
    
        socket.onopen = () => {
            console.log('[DEBUG] AI 服务器连接成功');
            isAiConnected = true;
            connectionStatus.classList.add('hidden');
            if (!gameOver && !isPaused && isAiMode) {
                requestAiMove();
            }
        };

        socket.onmessage = (event) => {
           try{
            console.log('[DEBUG] 收到消息:', event.data); // 打印收到的消息
            const data = JSON.parse(event.data);
            console.log('[DEBUG] 解析后的数据:', data); // 打印解析后的数据
            if (data.type === "move") {
                const targetX = data.targetX;
                const rotation = data.rotation;
                
                console.log(`[DEBUG] AI指令: targetX=${targetX}, rotation=${rotation}`);
                console.log(`[DEBUG] 当前方块位置: x=${currentPiece.x}, y=${currentPiece.y}`);
                
                // 执行AI指令 - 改进版本，直接计算最终位置
                executeAiMove(targetX, rotation);
    
                isAiThinking = false;
                document.getElementById('ai-status').classList.add('hidden');
            }
        }catch (error) {
                console.error('[ERROR] 解析服务器消息时出错:', error);
                isAiThinking = false;
                aiStatus.classList.add('hidden');
            }
        };
    
        socket.onclose = () => {
            isAiConnected = false;
            connectionStatus.classList.remove('hidden');
            console.log('[DEBUG] AI 服务器连接已关闭');
        };

        socket.onerror = () => {
            isAiConnected = false;
            connectionStatus.classList.remove('hidden');
            console.error('[ERROR] AI 服务器连接错误');
        };
    }

    // 断开AI服务器连接
    function disconnectFromAiServer() {
        if (socket) {
            socket.close();
            socket = null;
        }

        isAiConnected = false;
        isAiThinking = false;
        document.getElementById('connection-status').classList.add('hidden');
        document.getElementById('ai-status').classList.add('hidden');
    }

    // 执行AI移动指令
    function executeAiMove(targetX, rotationCount) {
        if (gameOver || isPaused || !currentPiece) {
            return;
        }

        console.log(`[DEBUG] 执行AI移动: 目标X=${targetX}, 旋转次数=${rotationCount}`);
        
        // 保存原始状态以备回退
        const originalShape = currentPiece.shape.map(row => [...row]);
        const originalX = currentPiece.x;
        const originalY = currentPiece.y;
        
        try {
            // 先执行旋转
            for (let i = 0; i < rotationCount; i++) {
                if (!executeRotation()) {
                    console.log(`[WARNING] 旋转失败在第${i+1}次旋转`);
                    // 如果旋转失败，恢复原状态并直接下落
                    currentPiece.shape = originalShape;
                    currentPiece.x = originalX;
                    currentPiece.y = originalY;
                    hardDrop();
                    return;
                }
            }
            
            // 然后移动到目标X位置
            if (!moveToTargetX(targetX)) {
                console.log(`[WARNING] 移动到目标位置失败: ${targetX}`);
            }
            
            // 最后执行硬下落
            hardDrop();
            
        } catch (error) {
            console.error('[ERROR] 执行AI移动时出错:', error);
            // 发生错误时恢复原状态并直接下落
            currentPiece.shape = originalShape;
            currentPiece.x = originalX;
            currentPiece.y = originalY;
            hardDrop();
        }
    }
    
    // 安全的旋转执行
    function executeRotation() {
        const rotated = [];
        for (let i = 0; i < currentPiece.shape[0].length; i++) {
            const row = [];
            for (let j = currentPiece.shape.length - 1; j >= 0; j--) {
                row.push(currentPiece.shape[j][i]);
            }
            rotated.push(row);
        }

        const previousShape = currentPiece.shape;
        currentPiece.shape = rotated;

        // 处理旋转后碰撞的情况（墙踢）
        if (checkCollision(currentPiece, currentPiece.x, currentPiece.y)) {
            // 尝试右移
            if (!checkCollision(currentPiece, currentPiece.x + 1, currentPiece.y)) {
                currentPiece.x++;
                return true;
            }
            // 尝试左移
            else if (!checkCollision(currentPiece, currentPiece.x - 1, currentPiece.y)) {
                currentPiece.x--;
                return true;
            }
            // 尝试上移（用于I型方块）
            else if (!checkCollision(currentPiece, currentPiece.x, currentPiece.y - 1)) {
                currentPiece.y--;
                return true;
            }
            // 尝试右移两格（用于I型方块）
            else if (!checkCollision(currentPiece, currentPiece.x + 2, currentPiece.y)) {
                currentPiece.x += 2;
                return true;
            }
            // 尝试左移两格（用于I型方块）
            else if (!checkCollision(currentPiece, currentPiece.x - 2, currentPiece.y)) {
                currentPiece.x -= 2;
                return true;
            }
            // 如果都不行，恢复原来的形状
            else {
                currentPiece.shape = previousShape;
                return false;
            }
        }
        
        return true;
    }
    
    // 移动到目标X位置
    function moveToTargetX(targetX) {
        const maxMoves = 20; // 防止无限循环
        let moveCount = 0;
        
        while (currentPiece.x !== targetX && moveCount < maxMoves) {
            const direction = targetX > currentPiece.x ? 1 : -1;
            const newX = currentPiece.x + direction;
            
            if (!checkCollision(currentPiece, newX, currentPiece.y)) {
                currentPiece.x = newX;
            } else {
                // 如果无法继续移动，停止尝试
                console.log(`[DEBUG] 无法移动到目标位置 ${targetX}, 当前位置 ${currentPiece.x}`);
                return false;
            }
            
            moveCount++;
        }
        
        if (moveCount >= maxMoves) {
            console.log(`[WARNING] 移动操作超过最大次数限制`);
            return false;
        }
        
        return currentPiece.x === targetX;
    }

    // 初始化游戏
    function init() {
        console.log('游戏初始化开始');
        board = Array(ROWS).fill().map(() => Array(COLS).fill(0));
        score = 0;
        lines = 0;
        level = 1;
        dropInterval = 1000;
        gameOver = false;
        isPaused = false;

        updateStats();
        resetBoard();
        newPiece();
        draw();
        console.log('游戏初始化完成');
        // 连接AI服务器
        if (isAiMode) {
            connectToAiServer();
        }

        if (isAiMode) {
            requestAiMove();
        }
    }

    // 向AI发送当前游戏状态并请求决策
    function requestAiMove() {
        if (!isAiMode || !isAiConnected || gameOver || isPaused || isAiThinking) {
            return;
        }

        isAiThinking = true;
        document.getElementById('ai-status').classList.remove('hidden');

        // 准备发送给AI的数据
        const data = {
            type: "state",
            board: board,
            piece: {
                shape: currentPiece.shape  // 明确指定 shape 字段
            },// 只发送形状
            lines_cleared: lines
        };

        // 发送数据到AI服务器
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(data));
        } else {
            console.error('WebSocket connection is not open');
            isAiThinking = false;
            document.getElementById('ai-status').classList.add('hidden');
        }
    }

    // 重置游戏区域
    function resetBoard() {
        for (let row = 0; row < ROWS; row++) {
            for (let col = 0; col < COLS; col++) {
                board[row][col] = 0;
            }
        }
    }

    // 创建新方块
    function newPiece() {
        if (!nextPiece) {
            nextPiece = randomPiece();
        }
    
        currentPiece = nextPiece;
        nextPiece = randomPiece();
    
        isAiThinking = false;
        document.getElementById('ai-status').classList.add('hidden');
        
        // 检查游戏是否结束
        if (checkCollision(currentPiece, currentPiece.x, currentPiece.y)) {
            gameOver = true;
            cancelAnimationFrame(animationId);
            draw();
            alert('游戏结束！得分: ' + score);
        }
    
        // 只在人类模式下上传分数
        if (!isAiMode && localStorage.getItem('user_id')) {
            fetch('/update_score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: localStorage.getItem('user_id'), score: score })
            })
            .then(response => response.json())
            .then(data => console.log('[分数上传成功]', data))
            .catch(error => console.error('[分数上传失败]', error));
        }
    
        // AI 模式逻辑保持不变
        if (isAiMode && isAiConnected && !gameOver && !isPaused) {
            requestAiMove();
        }
    }

    // 随机生成新方块
    function randomPiece() {
        const type = Math.floor(Math.random() * 7) + 1;
        const piece = {
            type: type,
            shape: SHAPES[type],
            x: Math.floor(COLS / 2) - Math.floor(SHAPES[type][0].length / 2),
            y: 0
        };
        return piece;
    }

    // 绘制游戏
    function draw() {
        ctx.fillStyle = '#1F2937';
        ctx.fillRect(0, 0, canvas.width, canvas.height);//背景清除

        // 绘制网格线
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.01)';
        ctx.lineWidth = 1;

        for (let row = 0; row < ROWS; row++) {
            for (let col = 0; col < COLS; col++) {
                ctx.strokeRect(col * BLOCK_SIZE, row * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
            }
        }

        // 绘制已落下的方块
        for (let row = 0; row < ROWS; row++) {
            for (let col = 0; col < COLS; col++) {
                if (board[row][col]) {
                    drawBlock(ctx, col, row, board[row][col]);
                }
            }
        }

        // 绘制当前方块
        if (currentPiece) {
            currentPiece.shape.forEach((row, y) => {
                row.forEach((value, x) => {
                    if (value) {
                        drawBlock(ctx, currentPiece.x + x, currentPiece.y + y, value);
                    }
                });
            });
        }

        // 如果游戏结束，显示游戏结束文字
        if (gameOver) {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = 'white';
            ctx.font = '24px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('游戏结束', canvas.width / 2, canvas.height / 2 - 20);
            ctx.fillText('得分: ' + score, canvas.width / 2, canvas.height / 2 + 20);
        }

        // 如果游戏暂停，显示暂停文字
        if (isPaused && !gameOver) {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = 'white';
            ctx.font = '24px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('游戏暂停', canvas.width / 2, canvas.height / 2);
        }
    }

    // 绘制单个方块
    function drawBlock(ctx, x, y, type) {
        const color = COLORS[type];

        // 方块阴影
        ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.fillRect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + 2, BLOCK_SIZE - 2, BLOCK_SIZE - 2);

        // 方块主体
        ctx.fillStyle = color;
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE - 2, BLOCK_SIZE - 2);

        // 方块高光
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE - 6, BLOCK_SIZE - 6);

        // 方块边框
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.strokeRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
    }

    // 移动方块
    function movePiece(dir) {
        if (gameOver || isPaused) return;

        const newX = currentPiece.x + dir;
        if (!checkCollision(currentPiece, newX, currentPiece.y)) {
            currentPiece.x = newX;
            draw();
        }
    }

    // 旋转方块
    function rotatePiece() {
        if (gameOver || isPaused) return;

        const rotated = [];
        for (let i = 0; i < currentPiece.shape[0].length; i++) {
            const row = [];
            for (let j = currentPiece.shape.length - 1; j >= 0; j--) {
                row.push(currentPiece.shape[j][i]);
            }
            rotated.push(row);
        }

        const previousShape = currentPiece.shape;
        currentPiece.shape = rotated;

        // 处理旋转后碰撞的情况（墙踢）
        if (checkCollision(currentPiece, currentPiece.x, currentPiece.y)) {
            // 尝试右移
            if (!checkCollision(currentPiece, currentPiece.x + 1, currentPiece.y)) {
                currentPiece.x++;
            }
            // 尝试左移
            else if (!checkCollision(currentPiece, currentPiece.x - 1, currentPiece.y)) {
                currentPiece.x--;
            }
            // 尝试上移（用于I型方块）
            else if (!checkCollision(currentPiece, currentPiece.x, currentPiece.y - 1)) {
                currentPiece.y--;
            }
            // 尝试右移两格（用于I型方块）
            else if (!checkCollision(currentPiece, currentPiece.x + 2, currentPiece.y)) {
                currentPiece.x += 2;
            }
            // 尝试左移两格（用于I型方块）
            else if (!checkCollision(currentPiece, currentPiece.x - 2, currentPiece.y)) {
                currentPiece.x -= 2;
            }
            // 如果都不行，恢复原来的形状
            else {
                currentPiece.shape = previousShape;
            }
        }

        draw();
    }

    // 方块下落
    function dropPiece() {
        if (gameOver || isPaused) return;

        if (!checkCollision(currentPiece, currentPiece.x, currentPiece.y + 1)) {
            currentPiece.y++;
        } else {
            lockPiece();
            clearLines();
            newPiece();
        }

        dropCounter = 0;
        draw();
    }

    // 快速下落（直接落到底部）
    function hardDrop() {
        if (gameOver || isPaused) return;

        while (!checkCollision(currentPiece, currentPiece.x, currentPiece.y + 1)) {
            currentPiece.y++;
            score += 2; // 快速下落得分
        }

        updateStats();
        dropPiece();
    }

    // 锁定方块（当方块不能再下落时）
    function lockPiece() {
        currentPiece.shape.forEach((row, y) => {
            row.forEach((value, x) => {
                if (value) {
                    const newX = currentPiece.x + x;
                    const newY = currentPiece.y + y;
                    if (newY >= ROWS) {
                        // 方块超出底部边界，游戏结束
                        gameOver = true;
                        cancelAnimationFrame(animationId);
                        draw();
                        alert('游戏结束！得分: ' + score);
                        return;
                    }
                    if (newY < 0) {
                        // 方块顶部超出屏幕，游戏结束
                        gameOver = true;
                        cancelAnimationFrame(animationId);
                        draw();
                        alert('游戏结束！得分: ' + score);
                        return;
                    }
                    board[newY][newX] = value;
                }
            });
        });
    }

    // 检查碰撞
    function checkCollision(piece, x, y) {
        for (let row = 0; row < piece.shape.length; row++) {
            for (let col = 0; col < piece.shape[row].length; col++) {
                if (piece.shape[row][col] !== 0) {
                    const newX = x + col;
                    const newY = y + row;

                    if (
                        newX < 0 ||
                        newX >= COLS ||
                        newY >= ROWS ||
                        newY < 0 || 
                        (newY >= 0 && board[newY][newX])
                    ) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // 清除已填满的行
    function clearLines() {
        let linesCleared = 0;

        for (let row = ROWS - 1; row >= 0; row--) {
            if (board[row].every(cell => cell !== 0)) {
                // 清除当前行
                board.splice(row, 1);
                // 在顶部添加新的空行
                board.unshift(Array(COLS).fill(0));
                linesCleared++;
                row++; // 重新检查当前行（现在是新的一行）
            }
        }

        if (linesCleared > 0) {
            // 计分规则：单行100分，双行300分，三行600分，四行1000分
            const linePoints = [0, 100, 300, 600, 1000];
            score += linePoints[linesCleared] * level;
            lines += linesCleared;

            // 每清除10行升级一次
            const newLevel = Math.floor(lines / 10) + 1;
            if (newLevel > level) {
                level = newLevel;
                // 速度随等级提升而增加（等级越高，间隔越短）
                dropInterval = Math.max(100, 1000 - (level - 1) * 100);
                speedElement.textContent = (1000 / dropInterval).toFixed(1);
            }

            updateStats();

            // 行清除动画
            animateLinesCleared(linesCleared);
        }
    }

    // 行清除动画
    function animateLinesCleared(linesCount) {
        // 简单的闪烁效果
        const originalFillStyle = ctx.fillStyle;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = originalFillStyle;

        setTimeout(() => {
            draw();
        }, 100);
    }

    // 更新游戏统计信息
    function updateStats() {
        scoreElement.textContent = score;
        linesElement.textContent = lines;
        levelElement.textContent = level;
        speedElement.textContent = (1000 / dropInterval).toFixed(1);
    }

    // 游戏循环
    let animationId = null;
    function gameLoop(time = 0) {
        if (gameOver || isPaused) return;

        const deltaTime = time - lastTime;
        lastTime = time;

        dropCounter += deltaTime;
        if (dropCounter > dropInterval) {
            dropPiece();
        }

        draw();
        animationId = requestAnimationFrame(gameLoop);
    }

    // 开始游戏
    function startGame() {
        if (gameOver) {
            init();
        }

        if (!isPaused) return;

        isPaused = false;
        lastTime = 0;
        dropCounter = 0;
        startButton.disabled = true;
        pauseButton.disabled = false;

        if (!gameOver) {
            gameLoop();
        }
    }

    // 暂停游戏
    function pauseGame() {
        if (gameOver) return;

        isPaused = true;
        startButton.disabled = false;
        pauseButton.disabled = true;

        cancelAnimationFrame(animationId);
    }

    // 重新开始游戏
    function restartGame() {
        init();
        startButton.disabled = true;
        pauseButton.disabled = false;

        if (!gameOver && !isPaused) {
            gameLoop();
        }
    }

    // 切换游戏模式
    function toggleGameMode() {
        isAiMode = !isAiMode;
        console.log(`[DEBUG] AI 模式切换: ${isAiMode}`);
        if (isAiMode) {
            // 切换到AI模式
            toggleDot.classList.add('translate-x-8');
            toggleDot.classList.remove('translate-x-0');
            humanModeButton.classList.remove('bg-primary/20', 'border-primary');
            humanModeButton.classList.add('bg-slate-700', 'border-slate-600');
            humanModeButton.querySelector('i').classList.remove('text-primary');
            humanModeButton.querySelector('i').classList.add('text-slate-500');
            aiModeButton.classList.remove('bg-slate-700', 'border-slate-600');
            aiModeButton.classList.add('bg-secondary/20', 'border-secondary');
            aiModeButton.querySelector('i').classList.remove('text-slate-500');
            aiModeButton.querySelector('i').classList.add('text-secondary');

            // 连接AI服务器
            connectToAiServer();
            requestAiMove(); // 立即请求首次决策
        } else {
            // 切换到人类模式
            toggleDot.classList.remove('translate-x-8');
            toggleDot.classList.add('translate-x-0');
            aiModeButton.classList.remove('bg-secondary/20', 'border-secondary');
            aiModeButton.classList.add('bg-slate-700', 'border-slate-600');
            aiModeButton.querySelector('i').classList.remove('text-secondary');
            aiModeButton.querySelector('i').classList.add('text-slate-500');
            humanModeButton.classList.remove('bg-slate-700', 'border-slate-600');
            humanModeButton.classList.add('bg-primary/20', 'border-primary');
            humanModeButton.querySelector('i').classList.remove('text-slate-500');
            humanModeButton.querySelector('i').classList.add('text-primary');

            // 断开AI连接
            disconnectFromAiServer();
        }

        // 如果游戏正在进行中，重新开始
        if (!gameOver && !isPaused) {
            restartGame();
        }
    }

    // 防止方向键滚动页面
    function preventScroll(event) {
        // 检查是否在人类模式且游戏未暂停
        if (!isAiMode && !isPaused) {
            // 方向键、空格键和P键
            const keys = {
                37: true, // 左
                38: true, // 上
                39: true, // 右
                40: true, // 下
                32: true, // 空格
                80: true  // P
            };

            if (keys[event.keyCode]) {
                event.preventDefault();
                return false;
            }
        }
    }

    // 键盘控制
    document.addEventListener('keydown', event => {
        preventScroll(event); // 防止滚动

        if (gameOver || isPaused || isAiMode) return;

        switch (event.key) {
            case 'ArrowLeft':
                movePiece(-1);
                break;
            case 'ArrowRight':
                movePiece(1);
                break;
            case 'ArrowDown':
                dropPiece();
                score += 1; // 缓慢下落得分
                updateStats();
                break;
            case 'ArrowUp':
                rotatePiece();
                break;
            case ' ':
                hardDrop();
                break;
            case 'p':
            case 'P':
                if (!gameOver) {
                    isPaused ? startGame() : pauseGame();
                }
                break;
        }
    });

    // 按钮事件监听
    startButton.addEventListener('click', startGame);
    pauseButton.addEventListener('click', pauseGame);
    restartButton.addEventListener('click', restartGame);
    modeToggle.addEventListener('click', toggleGameMode);
    humanModeButton.addEventListener('click', () => {
        if (!isAiMode) return;
        toggleGameMode();
    });
    aiModeButton.addEventListener('click', () => {
        if (isAiMode) return;
        toggleGameMode();
    });

    // 触摸设备支持（可选）
    let touchStartX = 0;
    let touchStartY = 0;

    canvas.addEventListener('touchstart', event => {
        if (gameOver || isPaused || isAiMode) return;

        touchStartX = event.touches[0].clientX;
        touchStartY = event.touches[0].clientY;
        event.preventDefault();
    }, false);

    canvas.addEventListener('touchmove', event => {
        event.preventDefault();
    }, false);

    canvas.addEventListener('touchend', event => {
        if (gameOver || isPaused || isAiMode) return;

        const touchEndX = event.changedTouches[0].clientX;
        const touchEndY = event.changedTouches[0].clientY;

        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;

        // 检测滑动方向
        if (Math.abs(diffX) > Math.abs(diffY)) {
            // 水平滑动
            if (diffX > 50) {
                movePiece(1); // 右
            } else if (diffX < -50) {
                movePiece(-1); // 左
            }
        } else {
            // 垂直滑动
            if (diffY > 50) {
                dropPiece(); // 下
            } else if (diffY < -50) {
                rotatePiece(); // 上（旋转）
            }
        }

        event.preventDefault();
    }, false);

    // 初始化游戏
    init();
}
document.addEventListener('DOMContentLoaded', () => {
    initTetris();
});
