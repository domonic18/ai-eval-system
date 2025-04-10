INSERT INTO users (username, email, hashed_password, display_name, avatar, is_active, is_admin)
VALUES 
('admin', 'admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '系统管理员', '/default-avatar.png', 1, 1);

INSERT INTO ai_models (name, provider, description, model_type, version, configuration, is_public, user_id, is_active)
VALUES 
('hk33smarter_api', 'HK33', 'HK33的API模型Demo', 'api', '1.0', '{"api_url": "https://guanghua-api.bj33smarter.com/v1"}', 1, 1, 1);

INSERT INTO datasets (
    name, 
    description, 
    category,
    type,
    file_path, 
    configuration, 
    user_id, 
    is_active
) VALUES 
(
    'demo_cmmlu_chat_gen', 
    '一个Demo演示数据集：中文通用语言理解测试，主要用于基础流程的测试验证', 
    'Demo演示', 
    'benchmark', 
    '/demo/demo_cmmlu_chat_gen', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'demo_math_chat_gen', 
    '一个Demo演示数据集：64条数学问题测试集，主要用于基础流程的测试验证', 
    'Demo演示', 
    'benchmark', 
    '/demo/demo_math_chat_gen', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'demo_gsm8k_chat_gen', 
    '一个Demo演示数据集：64条Grade School Math 8K数学问题集，主要用于基础流程的测试验证', 
    'Demo演示', 
    'benchmark', 
    '/demo/demo_gsm8k_chat_gen', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'cmmlu_gen', 
    '包含67个主题的综合性中文评估基准，专门用于评估语言模型在中文语境下的知识和推理能力', 
    '通用', 
    'benchmark', 
    '/data/cmmlu', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'GaokaoBench_gen', 
    '以中国高考题作为评测大语言模型能力的数据集，用以评估模型的语言能力和逻辑推理能力', 
    '通用', 
    'benchmark', 
    '/data/GAOKAOBench', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'gsm8k_gen', 
    '由OpenAI发布的8.5K高质量语言多样化小学数学应用题数据集，要求选择最合理的解决方案', 
    '数学', 
    'benchmark', 
    '/data/gsm8k', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'teval_zh_gen', 
    'T-Eval中文数据集，用于评估 复杂任务分解与规划能力 的基准测试集，重点关注模型将高层目标拆解为可执行子任务的系统性能力。', 
    '智能体', 
    'benchmark', 
    '/data/teval_zh', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'gaia_gen', 
    'GAIA数据集，这是一种严苛的评估Agent通用能力评测的数据集，其中包含165个任务，每个任务都需要agent借助外部工具来完成。', 
    '智能体', 
    'benchmark', 
    '/data/gaia', 
    '{"format": "chat"}', 
    1, 
    1
),
(
    'demo_hk33_chat_gen', 
    '一个用于Agent通用能力评测的数据集，包含：FewCLUE、BBH、MMLU-Pro、TruthfulQA各10条，主要用于评测Agent的基础语义理解能力、复杂任务推理能力、阐述事实的真实性以及安全性评测。', 
    '智能体', 
    'benchmark', 
    '/data/demo/demo_hk33_chat_gen', 
    '{"format": "chat"}', 
    1, 
    1
);