FROM python:3.10-slim

# 设置工作目录
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

# 1.3 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/app
ENV WORKING_DIR=/app/workspace

# 2. 复制项目文件
# 2.1 复制requirements文件
COPY requirements.txt .

# 2.2 复制项目文件
COPY apps/server /app/apps/server
# 2.3 复制项目根目录的setup.py文件到/app/setup.py
COPY setup.py /app/setup.py


# 3. 安装依赖
# 3.1 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3.2 安装项目依赖
RUN pip install --no-cache-dir -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 启动服务
# 4.1 启动服务
CMD ["uvicorn", "apps.server.src.main:app", "--host", "0.0.0.0", "--port", "8000"] 
