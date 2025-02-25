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