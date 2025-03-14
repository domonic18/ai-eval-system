# 直接使用nginx镜像，跳过构建阶段
FROM nginx:alpine

# 复制预构建的dist目录（路径调整为相对于项目根目录）
COPY apps/web/dist/ /usr/share/nginx/html/

# 复制nginx配置（路径调整为相对于项目根目录）
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 