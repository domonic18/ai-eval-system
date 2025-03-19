INSERT INTO users (username, email, hashed_password, display_name, avatar, is_active, is_admin)
VALUES 
('admin', 'admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '系统管理员', '/default-avatar.png', 1, 1);

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