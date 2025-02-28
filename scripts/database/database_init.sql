-- AI评测系统数据库初始化脚本
-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ai_eval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ai_eval;

-- 创建evaluations表
CREATE TABLE IF NOT EXISTS evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NULL COMMENT '任务名称',
    model_name VARCHAR(255) NOT NULL COMMENT '模型名称',
    dataset_name VARCHAR(255) NOT NULL COMMENT '数据集名称',
    model_configuration JSON NULL COMMENT '模型配置',
    dataset_configuration JSON NULL COMMENT '数据集配置',
    eval_config JSON NULL COMMENT '评估配置',
    status VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    task_id VARCHAR(255) NULL COMMENT 'Celery 任务 ID',
    error_message TEXT NULL COMMENT '错误信息',
    log_dir VARCHAR(255) NULL COMMENT '日志目录',
    progress FLOAT NOT NULL DEFAULT 0.0 COMMENT '进度百分比',
    results JSON NULL COMMENT '评估结果',
    user_id INT NULL COMMENT '用户ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (status),
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评估任务表';

-- 为存储的日志创建表
CREATE TABLE IF NOT EXISTS evaluation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evaluation_id INT NOT NULL COMMENT '评估ID',
    log_content TEXT NOT NULL COMMENT '日志内容',
    log_level VARCHAR(20) DEFAULT 'INFO' COMMENT '日志级别',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
    INDEX idx_evaluation_id (evaluation_id),
    INDEX idx_timestamp (timestamp),
    CONSTRAINT fk_logs_evaluation FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评估日志表';

-- 创建模型表（可以用于存储预定义的模型）
CREATE TABLE IF NOT EXISTS models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL COMMENT '模型名称',
    type VARCHAR(50) NOT NULL COMMENT '模型类型',
    provider VARCHAR(100) NULL COMMENT '提供者',
    path VARCHAR(255) NULL COMMENT '模型路径',
    api_base VARCHAR(255) NULL COMMENT 'API基础URL',
    description TEXT NULL COMMENT '描述',
    parameters JSON NULL COMMENT '默认参数',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_type (type),
    INDEX idx_provider (provider),
    UNIQUE INDEX unq_name_provider (name, provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型表';

-- 创建数据集表
CREATE TABLE IF NOT EXISTS datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL COMMENT '数据集名称',
    path VARCHAR(255) NULL COMMENT '数据集路径',
    format VARCHAR(50) NULL COMMENT '数据格式',
    description TEXT NULL COMMENT '描述',
    category VARCHAR(100) NULL COMMENT '分类',
    size INT NULL COMMENT '数据集大小',
    metrics JSON NULL COMMENT '评估指标',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_category (category),
    UNIQUE INDEX unq_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据集表';

-- 以下是未来可扩展的用户相关表
-- 如果需要添加用户功能，可以取消这些注释

-- CREATE TABLE IF NOT EXISTS users (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     username VARCHAR(50) NOT NULL COMMENT '用户名',
--     email VARCHAR(100) NOT NULL COMMENT '邮箱',
--     password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
--     is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
--     is_admin BOOLEAN DEFAULT FALSE COMMENT '是否管理员',
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
--     INDEX idx_username (username),
--     INDEX idx_email (email),
--     UNIQUE INDEX unq_username (username),
--     UNIQUE INDEX unq_email (email)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 如果需要用户关联功能，可以修改evaluations表添加user_id字段
-- ALTER TABLE evaluations ADD COLUMN user_id INT NULL COMMENT '创建者ID' AFTER results;
-- ALTER TABLE evaluations ADD CONSTRAINT fk_evaluations_user FOREIGN KEY (user_id) REFERENCES users(id);

-- 初始化一些默认数据
INSERT INTO models (name, type, provider, description)
VALUES 
('gpt-3.5-turbo', 'openai', 'OpenAI', 'OpenAI的GPT-3.5 Turbo模型'),
('hk33smarter_api', 'api', 'HK33', 'HK33 Smarter API模型');

INSERT INTO datasets (name, format, description, category)
VALUES 
('mmlu', 'json', 'Massive Multitask Language Understanding', '通用能力'),
('demo_cmmlu_chat', 'json', '中文通用语言理解测试', '中文理解'); 

-- 初始化管理员用户
INSERT INTO users (username, email, password_hash)
VALUES 
('admin', 'admin@example.com', 'admin');