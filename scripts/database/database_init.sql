-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_eval 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE ai_eval;

-- 用户表（新增时区字段）
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT '邮箱',
    avatar VARCHAR(255) COMMENT '头像URL',
    is_active BOOL DEFAULT TRUE COMMENT '是否激活',
    is_admin BOOL DEFAULT FALSE COMMENT '是否管理员',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    INDEX idx_user_username (username),
    INDEX idx_user_email (email)
) ENGINE=InnoDB COMMENT='用户表';

-- AI模型表（增加版本约束）
CREATE TABLE IF NOT EXISTS ai_models (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '模型ID',
    name VARCHAR(255) NOT NULL COMMENT '模型名称',
    provider VARCHAR(100) NOT NULL COMMENT '提供商',
    description TEXT COMMENT '模型描述',
    model_type VARCHAR(50) NOT NULL COMMENT '模型类型',
    version VARCHAR(50) COMMENT '版本',
    configuration JSON COMMENT '运行时配置',
    is_public BOOL DEFAULT TRUE COMMENT '可见性',
    is_active BOOL DEFAULT TRUE COMMENT '是否激活',
    user_id INT NOT NULL COMMENT '所属用户ID',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE INDEX uniq_model_name_version (name, version),
    INDEX idx_model_type (model_type)
) ENGINE=InnoDB COMMENT='AI模型表';

-- 数据集表（新增类型约束）
CREATE TABLE IF NOT EXISTS datasets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '数据集ID',
    name VARCHAR(255) NOT NULL COMMENT '数据集名称',
    description TEXT COMMENT '数据集描述',
    type VARCHAR(50) NOT NULL COMMENT '数据集类型',
    file_path VARCHAR(255) COMMENT '文件路径',
    configuration JSON COMMENT '数据集配置',
    is_active BOOL DEFAULT TRUE COMMENT '是否激活',
    user_id INT NOT NULL COMMENT '创建者ID',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE INDEX uniq_dataset_name (name),
    INDEX idx_dataset_type (type)
) ENGINE=InnoDB COMMENT='数据集表';

-- 竞技场表（状态枚举标准化）
CREATE TABLE IF NOT EXISTS arenas (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '竞技场ID',
    name VARCHAR(255) NOT NULL COMMENT '竞技场名称',
    description TEXT COMMENT '竞技场描述',
    status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending' COMMENT '状态',
    dataset_id INT NOT NULL COMMENT '数据集ID',
    configuration JSON COMMENT '竞技场配置',
    results JSON COMMENT '聚合结果',
    user_id INT NOT NULL COMMENT '创建者ID',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_arena_status (status),
    INDEX idx_arena_user (user_id)
) ENGINE=InnoDB COMMENT='竞技场表';

-- 竞技场参与者表（新增排名约束）
CREATE TABLE IF NOT EXISTS arena_participants (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '参与记录ID',
    arena_id INT NOT NULL COMMENT '竞技场ID',
    model_id INT NOT NULL COMMENT '模型ID',
    score FLOAT COMMENT '综合得分',
    `rank` INT COMMENT '排名',
    results JSON COMMENT '原始结果',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '参与时间',
    FOREIGN KEY (arena_id) REFERENCES arenas(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES ai_models(id) ON DELETE CASCADE,
    UNIQUE INDEX uniq_arena_model (arena_id, model_id),
    INDEX idx_participant_rank (`rank`)
) ENGINE=InnoDB COMMENT='竞技场参与者表';

-- 评估任务表（调整状态枚举）
CREATE TABLE IF NOT EXISTS evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '评估ID',
    name VARCHAR(255) COMMENT '任务名称',
    model_name VARCHAR(255) NOT NULL COMMENT '模型名称',
    dataset_names JSON COMMENT '数据集名称列表',
    model_configuration JSON COMMENT '模型配置',
    dataset_configuration JSON COMMENT '数据集配置',
    eval_config JSON COMMENT '评估配置',
    status ENUM('pending', 'running', 'completed', 'failed', 'stopped', 'terminated') DEFAULT 'pending' COMMENT '状态',
    task_id VARCHAR(255) COMMENT 'Celery任务ID',
    error_message TEXT COMMENT '错误信息',
    log_dir VARCHAR(255) COMMENT '日志目录',
    progress FLOAT DEFAULT 0.0 COMMENT '进度百分比',
    env_vars JSON COMMENT '环境变量',
    results JSON COMMENT '评估结果',
    user_id INT COMMENT '用户ID',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_eval_status (status),
    INDEX idx_eval_task_id (task_id)
) ENGINE=InnoDB COMMENT='评估任务表';


ALTER TABLE arena_participants 
MODIFY model_id INT NOT NULL COMMENT '模型ID',
ADD FOREIGN KEY (model_id) REFERENCES ai_models(id) ON DELETE CASCADE;

-- 初始化一些默认数据
INSERT INTO ai_models (name, provider, description, model_type, version, configuration, is_public, user_id, is_active)
VALUES 
('hk33smarter_api', 'HK33', 'HK33 Smarter API模型', 'api', '1.0', '{"api_url": "https://api.hk33.com/v1"}', 1, 1, 1);

INSERT INTO datasets (name, description, type, file_path, configuration, user_id, is_active)
VALUES 
('demo_cmmlu_chat_gen', '一个中文通用语言理解测试的Demo', 'benchmark', '/demo/demo_cmmlu_chat_gen/', '{"format": "chat"}', 1, 1),
('demo_math_chat_gen', '一个64条数学问题测试集的Demo', 'benchmark', '/demo/demo_math_chat_gen/', '{"format": "chat"}', 1, 1),
('demo_gsm8k_chat_gen', '一个64条Grade School Math 8K数学问题集的Demo', 'benchmark', '/demo/demo_gsm8k_chat_gen/', '{"format": "chat"}', 1, 1),
('ceval', '中文多学科知识评估基准', 'benchmark', '/data/ceval/', '{"format": "mcq"}', 1, 1),
('humaneval', '代码生成能力评估（164道编程题）', 'benchmark', '/code/humaneval/', '{"task": "code_generation"}', 1, 1),
('hellaswag', 'HellaSwag常识推理测试', 'benchmark', '/data/hellaswag/', '{"split": "test"}', 1, 1);
-- 初始化管理员用户
INSERT INTO users (username, email, password_hash)
VALUES 
('admin', 'admin@example.com', 'admin');