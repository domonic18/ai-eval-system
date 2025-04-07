FROM python:3.10-slim

WORKDIR /app

# 1. 前置操作及环境准备
# 1.1 配置 Debian 华为云镜像源
RUN echo "deb https://mirrors.huaweicloud.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
 && echo "deb https://mirrors.huaweicloud.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
 && echo "deb https://mirrors.huaweicloud.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 1.2 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    libmariadb-dev-compat \
    && rm -rf /var/lib/apt/lists/*

# 1.3 创建专用用户
RUN adduser --disabled-password --gecos "" appuser

# 给appuser用户足够权限
RUN usermod -a -G root appuser

# 2. 复制项目文件
# 2.1 复制requirements文件
COPY requirements.txt .

# 2.2 复制项目文件和OpenCompass源码
COPY apps/server /app/apps/server
COPY libs/OpenCompass /app/libs/OpenCompass

# 2.3 复制custom_api.py文件到/app/libs/OpenCompass/opencompass/configs/models/openai下面
COPY scripts/eval_script/custom_api.py /app/libs/OpenCompass/opencompass/configs/models/openai/custom_api.py
COPY scripts/eval_script/demo_hk33_chat_gen.py /app/libs/OpenCompass/opencompass/configs/datasets/demo/demo_hk33_chat_gen.py

# 2.4 复制项目根目录的setup.py文件到/app/setup.py
COPY setup.py /app/setup.py


# 3. 安装依赖
# 3.1 安装OpenCompass
RUN pip install --no-cache-dir -e /app/libs/OpenCompass -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3.2 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3.3 安装项目依赖
RUN pip install --no-cache-dir -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
# 3.4 安装modelscope
RUN pip install --no-cache-dir modelscope[framework] -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3.5 安装T-eval
RUN pip install --no-cache-dir lagent==0.1.2 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 设置环境变量和目录
# 4.1 设置环境变量
ENV DATASET_SOURCE=ModelScope
ENV HF_ENDPOINT=https://hf-mirror.com
ENV COMPASS_DATA_CACHE=/app/workspace/opencompass \
    HF_HOME=/app/workspace/huggingface \
    MODELSCOPE_CACHE=/app/workspace/modelscope
ENV PYTHONPATH=/app
ENV WORKING_DIR=/app/workspace
ENV OPENCOMPASS_WORK_DIR=${WORKING_DIR}/opencompass
ENV PYTHONUNBUFFERED=1

# 4.2 创建目录并赋权
RUN mkdir -p ${WORKING_DIR}/logs ${WORKING_DIR}/data ${OPENCOMPASS_WORK_DIR} \
    /app/workspace/opencompass \
    /app/workspace/huggingface \
    /app/workspace/modelscope && \
    chown -R appuser:appuser ${WORKING_DIR} \
    /app/workspace/opencompass \
    /app/workspace/huggingface \
    /app/workspace/modelscope

# 4.3 切换用户
USER appuser

    
# 4.4 启动服务
CMD ["uvicorn", "apps.server.src.main:app", "--host", "0.0.0.0", "--port", "8000"] 