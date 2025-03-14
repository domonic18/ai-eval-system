FROM python:3.10-slim

WORKDIR /app

# 配置 Debian 华为云镜像源
RUN echo "deb https://mirrors.huaweicloud.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
 && echo "deb https://mirrors.huaweicloud.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
 && echo "deb https://mirrors.huaweicloud.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    libmariadb-dev-compat \
    && rm -rf /var/lib/apt/lists/*


# 创建专用用户
RUN adduser --disabled-password --gecos "" appuser

# 先复制requirements文件
COPY requirements.txt .

# 提前安装主要依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件和OpenCompass源码
COPY . .
COPY ../../libs/OpenCompass /app/libs/OpenCompass

# 复制custom_api.py文件到/app/libs/OpenCompass/opencompass/configs/models/openai下面
COPY ../../workspace/eval_script/custom_api.py /app/libs/OpenCompass/opencompass/configs/models/openai/custom_api.py

# 安装OpenCompass
RUN pip install --no-cache-dir -e /app/libs/OpenCompass -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目根目录的setup.py文件到/app/setup.py
COPY setup.py /app/setup.py

# 安装项目依赖
RUN pip install --no-cache-dir -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 设置环境变量
ENV PYTHONPATH=/app
ENV WORKING_DIR=/app/workspace
ENV OPENCOMPASS_WORK_DIR=${WORKING_DIR}/opencompass

# 创建目录并赋权
RUN mkdir -p ${WORKING_DIR}/logs ${WORKING_DIR}/data ${OPENCOMPASS_WORK_DIR} && \
    chown -R appuser:appuser ${WORKING_DIR}

# 切换用户
USER appuser

CMD ["uvicorn", "apps.server.src.main:app", "--host", "0.0.0.0", "--port", "8000"] 