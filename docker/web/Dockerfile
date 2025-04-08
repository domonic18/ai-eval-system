# 使用Node.js镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量
ARG NODE_ENV=development
ENV NODE_ENV=${NODE_ENV}
ENV CHOKIDAR_USEPOLLING=true
ENV HOST=0.0.0.0

ARG DOCKER_ENV
ENV VITE_DOCKER_ENV=$DOCKER_ENV

# 设置npm镜像源解决网络问题
# RUN npm config set registry https://registry.npmmirror.com/

# 复制package.json和package-lock.json
COPY apps/web/package*.json ./

# 安装依赖（添加重试机制和超时设置）
RUN npm install

# 复制源代码
COPY apps/web/ ./

# 暴露开发服务器端口
EXPOSE 5173

# 启动开发服务器
CMD ["npm", "run", "dev"]

