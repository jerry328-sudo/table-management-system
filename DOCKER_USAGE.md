# 服务器使用登记系统 - Docker 部署指南

## 概述
这个Docker容器包含了完整的服务器使用登记系统，可以轻松部署到任何支持Docker的环境中。

## 系统要求
- Docker 20.0+ 
- Docker Compose 1.29+ (可选，但推荐)
- 至少 512MB 可用内存
- 至少 1GB 可用磁盘空间

## 快速启动

### 方法一：使用 Docker Compose (推荐)

1. **克隆或下载项目文件**
   ```bash
   # 确保你有以下文件：
   # - Dockerfile
   # - docker-compose.yml
   # - app.py
   # - requirements.txt
   # - templates/ 目录
   # - static/ 目录（如果存在）
   ```

2. **启动服务**
   ```bash
   docker-compose up -d
   ```

3. **访问应用**
   打开浏览器访问：`http://localhost:5000`

### 方法二：使用 Docker 命令

1. **构建镜像**
   ```bash
   docker build -t table-management-system .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name table-system \
     -p 5000:5000 \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/backups:/app/backups \
     table-management-system
   ```

## 数据持久化

系统使用Excel文件存储数据，为了确保数据不丢失，请：

1. **创建数据目录**
   ```bash
   mkdir -p data backups
   ```

2. **挂载数据卷**
   - `./data:/app/data` - 存储主要数据文件
   - `./backups:/app/backups` - 存储备份文件
   - `./*.xlsx:/app/` - 挂载现有的Excel文件

## 环境变量配置

可以通过环境变量自定义配置：

```bash
# 设置Flask环境为生产模式
FLASK_ENV=production

# 设置端口（默认5000）
PORT=5000
```

## 常用操作

### 查看容器状态
```bash
docker-compose ps
# 或
docker ps
```

### 查看日志
```bash
docker-compose logs -f
# 或
docker logs -f table-system
```

### 停止服务
```bash
docker-compose down
# 或
docker stop table-system
```

### 重启服务
```bash
docker-compose restart
# 或
docker restart table-system
```

### 更新应用
```bash
# 停止现有服务
docker-compose down

# 重新构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 备份和恢复

### 备份数据
```bash
# 备份所有数据文件
docker cp table-system:/app/5520_records.xlsx ./backup_5520_$(date +%Y%m%d).xlsx
docker cp table-system:/app/9755_records.xlsx ./backup_9755_$(date +%Y%m%d).xlsx

# 或者直接备份data目录
tar -czf backup_$(date +%Y%m%d).tar.gz data/ backups/
```

### 恢复数据
```bash
# 恢复数据文件到容器
docker cp ./backup_5520.xlsx table-system:/app/5520_records.xlsx
docker cp ./backup_9755.xlsx table-system:/app/9755_records.xlsx

# 重启容器以应用更改
docker-compose restart
```

## 健康检查

容器包含健康检查功能，可以监控应用状态：

```bash
# 检查容器健康状态
docker inspect --format='{{.State.Health.Status}}' table-system
```

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口使用情况
   netstat -tulpn | grep :5000
   
   # 修改docker-compose.yml中的端口映射
   ports:
     - "8080:5000"  # 改为使用8080端口
   ```

2. **权限问题**
   ```bash
   # 确保数据目录有正确权限
   sudo chown -R 1000:1000 data/ backups/
   ```

3. **内存不足**
   ```bash
   # 检查系统资源
   docker stats
   
   # 增加容器内存限制
   docker run --memory="1g" ...
   ```

4. **数据文件丢失**
   ```bash
   # 检查数据卷挂载
   docker inspect table-system | grep Mounts -A 10
   
   # 确保备份目录存在
   ls -la backups/
   ```

### 调试模式

如果需要调试，可以使用开发模式：

```bash
# 使用开发模式启动
docker run -it \
  --rm \
  -p 5000:5000 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
  table-management-system
```

## 生产环境部署建议

1. **使用反向代理**
   - 配置Nginx或Apache作为反向代理
   - 启用HTTPS
   - 设置适当的缓存策略

2. **监控和日志**
   ```bash
   # 配置日志轮转
   docker-compose.yml中添加：
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

3. **定期备份**
   ```bash
   # 设置定时备份任务
   crontab -e
   # 添加：0 2 * * * /path/to/backup-script.sh
   ```

4. **安全设置**
   - 确保容器以非root用户运行
   - 定期更新基础镜像
   - 限制容器资源使用

## 支持和联系

如果遇到问题，请检查：
1. Docker和Docker Compose版本
2. 系统资源使用情况
3. 日志文件中的错误信息
4. 网络连接和端口配置

---

© 2025 服务器使用登记系统 Docker版