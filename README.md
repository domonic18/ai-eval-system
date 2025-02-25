# ai-eval-system
这是一个基于OpenCompass的模型评测系统，该系统提供了前端页面UI以方便用户自助开展评测工作。


## 目录结构
```
ai-eval-system/
├── .git/                   # Git仓库
├── .gitmodules             # 子模块配置
├── apps/                   # 主应用目录
│   ├── web/                # 前端工程（独立的git仓库）
│   │   ├── src/
│   │   └── package.json
│   ├── server/             # 后端服务（独立的git仓库）
│   │   ├── src/
│   │   └── requirements.txt
│   └── engine/             # 评测引擎封装层
├── libs/                   # 第三方依赖库
│   └── OpenCompass/        # 通过git子模块引入（保持独立更新）
├── configs/                # 分层配置文件
│   ├── environments/       # 环境特定配置
│   │   ├── dev.yaml
│   │   └── prod.yaml
│   └── deploy/             # 部署配置文件
├── docs/                   # 项目文档
│   ├── ARCHITECTURE.md     # 架构设计文档
│   └── DEVELOPMENT.md      # 开发规范
├── scripts/                # 运维脚本
│   ├── deploy.sh
│   └── migrate_db.py
├── tests/                  # 分层测试目录
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── third_party/            # 可能改造的第三方代码
├── docker/                 # 容器化配置
│   ├── web.dockerfile
│   └── server.dockerfile
└── .gitignore              # 全局忽略规则
```

## 项目构成
### 1. 分层架构设计
- 前端层：Vue3/React + TypeScript + WebSocket（实时状态）
- 网关层：Nginx（反向代理/负载均衡/SSL终结）
- 服务层：
- API服务：FastAPI/DRF（RESTful API）
  - 异步任务引擎：Celery + RabbitMQ/Redis（分布式任务队列）
  - 核心评测引擎：OpenCompass封装层（Python API调用）
- 持久层：
  - PostgreSQL（关系型数据）
  - MinIO (S3兼容对象存储，用于大文件)
  - Redis（缓存/消息中间件）


## 快速开始
### 1. 创建虚拟环境
```bash
conda create -n eval python=3.10
conda activate eval
```

### 2. 安装依赖
```bash
cd apps/server/src
pip install -r requirements.txt
```
> 清华源：https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple


## 3. 启动服务

### 正常启动流程

1. **启动Redis服务** (用于Celery任务队列)
```bash
# 如果使用Docker方式
docker run -d -p 6379:6379 --name redis-server redis:alpine

# 或者使用本地Redis
brew services start redis  # macOS
sudo service redis-server start  # Ubuntu/Debian
```

2. **启动FastAPI服务器**
```bash
cd apps/server
python start_fastapi_server.py
```
服务器将在 http://localhost:8000 启动，可以通过访问 http://localhost:8000/docs 查看API文档。

3. **启动Celery Worker**
```bash
cd apps/server
python start_celery_worker.py
```
这将启动Celery Worker处理异步评测任务。

### 调试流程

#### API服务器调试

1. **VS Code调试模式**
   - 在VS Code中打开项目
   - 在运行和调试视图中选择 "FastAPI 直接调试" 配置
   - 点击绿色播放按钮启动调试会话
   - 设置断点后开始调试

2. **远程调试模式**
   - 启动调试服务器
     ```bash
     cd apps/server
     python debug_fastapi_server.py
     ```
   - 在VS Code中选择 "FastAPI 远程调试" 配置
   - 点击绿色播放按钮连接到调试服务器

#### Celery Worker调试

1. **VS Code调试模式**
   - 启动调试版Celery Worker
     ```bash
     cd apps/server
     python debug_celery_worker.py
     ```
   - 在VS Code中选择 "Celery Worker 调试" 配置
   - 点击绿色播放按钮连接到Celery调试服务器
   - 任务处理时会在设置的断点处停下

2. **测试任务发送**
   ```bash
   cd apps/server
   python test_eval_task.py
   ```

## 常见问题与解决方案

### 数据库连接问题

1. **PostgreSQL连接失败**
   
   症状：启动时出现 `connection to server at "localhost", port 5432 failed: Connection refused`
   
   解决方案：
   - 检查PostgreSQL服务是否运行
   - 编辑 `.env` 文件，使用SQLite作为替代
     ```
     DB_URL=sqlite:///./ai_eval.db
     ```
   - 或通过环境变量强制使用SQLite
     ```python
     os.environ["DB_URL"] = "sqlite:///./ai_eval.db"
     ```

### Redis连接问题

1. **Redis连接被拒绝**
   
   症状：出现 `Connection refused` 错误
   
   解决方案：
   - 确认Redis服务正在运行
   - 如果使用Docker，检查容器是否启动：`docker ps | grep redis`
   - 检查端口映射是否正确
   - 如果需要，使用容器IP地址：编辑 `.env` 文件中的 `REDIS_URL`

2. **对于开发环境不想使用Redis**
   
   解决方案：
   - 修改 `celery_app.py` 使用内存模式
     ```python
     celery_app = Celery(
         "ai_eval_tasks",
         broker='memory://',
         backend='memory://'
     )
     ```

### Celery任务问题

1. **Worker无法接收任务**
   
   症状：`Received unregistered task of type 'xxx'`
   
   解决方案：
   - 确保任务注册时使用显式名称
     ```python
     @celery_app.task(bind=True, name='eval_task.run_evaluation')
     def run_evaluation(self, eval_id):
         # ...
     ```
   - 使用相同的Python路径导入模块
   - 检查 `celery_app.py` 中的 `include` 设置是否正确

2. **OpenCompass路径问题**
   
   解决方案：
   - 在 `eval_tasks.py` 中使用绝对路径
     ```python
     BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
     OPENCOMPASS_PATH = os.path.join(BASE_DIR, "libs", "OpenCompass")
     ```

### 调试器问题

1. **Python 3.13兼容性问题**
   
   症状：debugpy出现错误 `Error on build_exception_info_response`
   
   解决方案：
   - 使用Python 3.9-3.11版本创建虚拟环境
     ```bash
     conda create -n eval-debug python=3.11
     conda activate eval-debug
     ```
   - 或使用普通运行方式并添加print语句

2. **调试器使用错误Python解释器**
   
   解决方案：
   - 在VS Code中选择正确的解释器 (Ctrl+Shift+P -> Python: Select Interpreter)
   - 在 `launch.json` 中添加 `"python": "${command:python.interpreterPath}"`

### 其他问题




