# ai-eval-system
这是一个基于OpenCompass的模型评测系统，该系统提供了前端页面UI以方便用户自助开展评测工作。

## 项目工程运作整体流程

### 系统架构流程
```
┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐    ┌───────────────┐
│             │    │             │    │                     │    │               │
│  前端应用   │───▶│  FastAPI    │───▶│  Celery 任务队列    │───▶│ OpenCompass   │
│  (Vue/React)│    │  服务       │    │  (Redis/RabbitMQ)   │    │ 评测引擎      │
│             │◀───│             │◀───│                     │◀───│               │
└─────────────┘    └─────────────┘    └─────────────────────┘    └───────────────┘
      │                  │                       │                       │
      │                  │                       │                       │
      │                  ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                             数据存储层                                      │
│                  (SQLite/PostgreSQL + Redis + MinIO/S3)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据流程
1. **用户请求流程**：
   - 用户通过前端界面提交评测请求
   - 请求包含模型配置、数据集选择和评测参数
   - 前端将请求发送到FastAPI后端服务

2. **后端处理流程**：
   - FastAPI接收请求并验证参数
   - 创建评测任务记录并存储在数据库中
   - 将任务提交到Celery异步队列处理
   - 返回任务ID和状态给前端

3. **异步评测流程**：
   - Celery Worker接收任务
   - 准备评测环境和参数
   - 调用OpenCompass评测引擎执行实际评测
   - 实时更新评测进度和状态
   - 评测完成后存储结果

4. **结果查询流程**：
   - 前端定期轮询或通过WebSocket接收任务状态更新
   - 任务完成后获取评测结果和分析数据
   - 将结果以图表和报告形式展示给用户



### 关键技术组件
1. **FastAPI**: 提供高性能API服务，支持异步请求处理和自动API文档生成
2. **SQLAlchemy**: ORM框架，实现数据模型与数据库的映射
3. **Celery**: 分布式任务队列，处理长时间运行的评测任务
4. **Redis**: 作为Celery的消息代理和后端存储，同时提供缓存功能
5. **OpenCompass**: 核心评测引擎，提供模型性能评估能力

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

### 代码组织结构
后端服务采用模块化设计，主要组件包括：

```
apps/server/
├── src/                      # 源代码目录
│   ├── db/                   # 数据库相关模块
│   │   ├── __init__.py       # 模块初始化文件
│   │   └── database.py       # 数据库连接和会话管理
│   ├── models/               # 数据模型定义
│   │   └── eval.py           # 评测相关数据模型
│   ├── schemas/              # 数据验证和序列化模式
│   │   └── eval.py           # 评测API数据模式
│   ├── services/             # 业务逻辑服务
│   │   └── eval_service.py   # 评测服务实现
│   ├── routers/              # API路由模块
│   │   └── eval.py           # 评测API路由定义
│   ├── tasks/                # 异步任务定义
│   │   └── eval_tasks.py     # 评测任务实现
│   ├── celery_app.py         # Celery应用配置
│   ├── config.py             # 应用配置管理
│   └── main.py               # 主应用入口
├── tests/                    # 测试代码目录
│   ├── api/                  # API测试
│   ├── unit/                 # 单元测试
│   └── integration/          # 集成测试
├── requirements.txt          # 依赖项清单
├── start_fastapi_server.py   # 启动FastAPI服务器脚本
└── start_celery_worker.py    # 启动Celery Worker脚本
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
### 1. 拉取代码
```bash
git clone https://github.com/OpenCompass/ai-eval-system.git
cd ai-eval-system

# 拉取子模块
git submodule update --init --recursive
```

### 2. 创建虚拟环境
```bash
conda create -n eval python=3.10
conda activate eval
```

### 2. 安装依赖
```bash
cd apps/server
pip install -r requirements.txt

# 安装OpenCompass
cd ../../libs/OpenCompass
pip install -e .
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




