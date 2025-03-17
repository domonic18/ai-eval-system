#!/bin/bash

# 获取脚本所在目录绝对路径
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# 1. 拷贝custom_api.py文件
SOURCE_FILE="${SCRIPT_DIR}/../scripts/eval_script/custom_api.py"
TARGET_DIR="${SCRIPT_DIR}/../libs/OpenCompass/opencompass/configs/models/openai"

echo "正在拷贝配置文件..."
if mkdir -p "$TARGET_DIR" && cp "$SOURCE_FILE" "$TARGET_DIR"; then
    echo "✅ 文件拷贝成功：${SOURCE_FILE} -> ${TARGET_DIR}/custom_api.py"
else
    echo "❌ 文件拷贝失败，请检查路径是否正确" >&2
    exit 1
fi

# 2. 运行初始化数据库脚本
INIT_SCRIPT="${SCRIPT_DIR}/init_database.py"

echo "正在初始化数据库..."
if python3 "$INIT_SCRIPT"; then
    echo "✅ 数据库初始化成功"
else
    echo "❌ 数据库初始化失败" >&2
    exit 1
fi
