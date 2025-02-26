#!/bin/bash
# MySQL初始化脚本

# 定义变量（可以根据需要修改）
DB_NAME="ai_eval"
DB_USER="ai_eval_user"
DB_PASSWORD="ai_eval_password"
DB_ROOT_PASSWORD="abc123456"

# 检查是否安装了MySQL客户端
if ! command -v mysql &> /dev/null; then
    echo "错误: MySQL客户端未安装，请先安装MySQL客户端"
    echo "在Ubuntu可使用: sudo apt install mysql-client"
    echo "在macOS可使用: brew install mysql-client"
    exit 1
fi

# 创建数据库和用户
echo "正在创建数据库和用户..."
mysql -h 127.0.0.1 -P 3306 --protocol=tcp \
  -u root -p"$DB_ROOT_PASSWORD" \
  --connect-timeout=5 \
  <<EOF
-- 创建数据库
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示数据库和用户
SHOW DATABASES;
SELECT user, host FROM mysql.user WHERE user = '$DB_USER';
EOF

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "✅ 数据库和用户创建成功！"
    echo "数据库名称: $DB_NAME"
    echo "用户名: $DB_USER"
    echo "密码: $DB_PASSWORD"
    
    # 创建.env文件
    echo "正在创建.env文件..."
    cat > ../.env <<EOL
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=$DB_USER
MYSQL_PASSWORD=$DB_PASSWORD
MYSQL_DB=$DB_NAME

# Redis配置
REDIS_URL=redis://localhost:6379/0

# OpenCompass路径
OPENCOMPASS_PATH=../../libs/OpenCompass
EOL
    
    echo "✅ .env文件已创建在apps/server/.env"
else
    echo "❌ 数据库和用户创建失败，请检查MySQL连接和权限"
fi 