# ai-eval-system
这是一个基于OpenCompass的模型评测系统，该系统提供了前端页面UI以方便用户自助开展评测工作。

## 版本发布
v0.1：
- 支持基于OpenCompass的B/S架构的模型评测
- 支持API方式提交评测任务
- 支持评测任务的队列管理功能，包括创建、排队、运行、终止等
- 支持评测过程的日志的实时监控
- 支持评测结果的导出



## 项目架构

### 系统架构流程
```
┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐    ┌───────────────┐
│             │    │             │    │                     │    │               │
│  前端应用    │───▶│  FastAPI    │───▶│  Celery 任务队列      │───▶│ OpenCompass   │
│  (Vue/React)│    │  服务       │     │  (Redis)            │    │ 评测引擎       │
│             │◀───│             │◀───│                     │◀───│               │
└─────────────┘    └─────────────┘    └─────────────────────┘    └───────────────┘
      │                  │                       │                       │
      │                  │                       │                       │
      │                  ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                             数据存储层                                        │
│                          (MySQL + Redis )                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
### 1. 分层架构设计
- 前端层：Vue3/React + TypeScript + WebSocket（实时状态）
- 服务层：
- API服务：FastAPI/DRF（RESTful API）
  - 异步任务引擎：Celery + Redis（分布式任务队列）
  - 核心评测引擎：OpenCompass封装层（Python API调用）
- 持久层：
  - PostgreSQL（关系型数据）
  - Redis（缓存/消息中间件）


### 2. 关键技术组件
1. **FastAPI**: 提供高性能API服务，支持异步请求处理和自动API文档生成
2. **SQLAlchemy**: ORM框架，实现数据模型与数据库的映射
3. **Celery**: 分布式任务队列，处理长时间运行的评测任务
4. **Redis**: 作为Celery的消息代理和后端存储，同时提供缓存功能
5. **OpenCompass**: 核心评测引擎，提供模型性能评估能力

### 3. 目录结构
```
ai-eval-system/
├── apps/                        # 主应用目录
│   ├── web/                     # 前端工程（独立的git仓库）
│   │   ├── src/
│   │   └── package.json
│   ├── server/                  # 后端服务（独立的git仓库）
│   │   ├── src/
├── libs/                        # 第三方依赖库
│   └── OpenCompass/             # 通过git子模块引入（保持独立更新）
├── docs/                        # 项目文档
│   └── 架构设计文档.md            # 开发规范
├── scripts/                     # 运维脚本
│   ├── init_database.py         # 初始化数据库
│   └── start_celery_worker.py   # 启动Celery Worker
│   └── start_fastapi_server.py  # 启动FastAPI服务器
├── docker/                      # 容器化配置
```

## 快速部署
### 1. 拉取代码
```bash
git clone https://github.com/domonic18/ai-eval-system.git
cd ai-eval-system

# 拉取子模块
git submodule update --init --recursive
```

### 2. 创建虚拟环境
```bash
conda create -n eval python=3.10
conda activate eval
```

### 3. 配置环境变量
```bash
cp .env.example .env
```
编辑.env文件，配置数据库连接信息


### 4. 安装依赖
```bash
# 安装基础依赖
cd requirements
pip install -r base.txt

# 安装ai-eval-system
cd 根目录
pip install -e .

# 安装OpenCompass
cd libs/OpenCompass
pip install -e .
```
> 清华源：https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

## 3. 启动服务

### 正常启动流程

1. **启动Redis服务** (用于Celery任务队列)
```bash
# 如果使用Docker方式
docker run -d -p 6379:6379 --name redis-server redis:alpine
```

2. **启动Mysql服务器**
```bash
docker run -d -p 3306:3306 --name mysql-server mysql:8.0
```

3. **初始化数据库**
```bash
cd scripts
python init_database.py
```

4. **启动FastAPI服务器**
```bash
cd apps/server
python start_fastapi_server.py
```
服务器将在 http://localhost:8000 启动，可以通过访问 http://localhost:8000/docs 查看API文档。

5. **启动Celery Worker**
```bash
cd apps/server
python start_celery_worker.py
```
这将启动Celery Worker处理异步评测任务。

6. **启动前端服务**
```bash
cd apps/web
npm install
npm run dev
```
前端服务将在 http://localhost:8080 启动，可以通过访问 http://localhost:8080 查看评测系统UI。


## TODO
前端页面
- [ ] 支持数据集的基础后台管理功能，包括增、删、改、查
- [ ] 支持模型基础后台管理功能，包括增、删、改、查
- [ ] 支持评测榜单功能，实现评测结果的可视化
- [ ] 支持评测结果的导出
- [ ] 支持数据集在线化编辑功能

基础建设
- [ ] 支持Docker化部署



