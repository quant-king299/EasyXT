# 🚀 EasyXT实时数据推送系统 - PTQMT网站集成部署指南

## 📋 概述说明

### 您的服务器配置
- **服务器**: 阿里云 2核2G内存 50GB硬盘 3M带宽
- **主网站**: www.ptqmt.com
- **EasyXT系统**: 量化交易数据推送服务

### 系统关系图解
```
┌─────────────────────────────────────────────────────────────┐
│                    阿里云服务器 (2C2G)                        │
├─────────────────────────────────────────────────────────────┤
│  端口80/443: www.ptqmt.com (主网站)                          │
│  ├── 网站首页、用户界面、静态资源                              │
│  └── 可以嵌入EasyXT数据展示页面                               │
├─────────────────────────────────────────────────────────────┤
│  端口8080: EasyXT API服务 (后台数据服务)                      │
│  ├── RESTful API接口                                        │
│  ├── WebSocket实时推送                                       │
│  └── 数据处理和缓存                                          │
├─────────────────────────────────────────────────────────────┤
│  端口8081: EasyXT管理界面 (可选)                              │
│  ├── 系统监控面板                                            │
│  ├── 配置管理界面                                            │
│  └── 日志查看工具                                            │
└─────────────────────────────────────────────────────────────┘
```

## 🔗 网站集成关系详解

### 1. 独立但互补的关系
- **主网站 (www.ptqmt.com)**: 您的门户网站，展示公司信息、产品介绍等
- **EasyXT系统**: 作为后台数据服务，为主网站提供实时金融数据

### 2. 集成方式选择

#### 方案A: 完全独立运行
```
www.ptqmt.com (端口80)     ←→     用户访问主网站
api.ptqmt.com (端口8080)   ←→     EasyXT数据API服务
```

#### 方案B: 主网站集成数据展示
```
www.ptqmt.com/
├── index.html              (主页)
├── about.html              (关于我们)
├── products.html           (产品介绍)
└── data/                   (数据展示页面，调用EasyXT API)
    ├── realtime.html       (实时行情)
    ├── analysis.html       (数据分析)
    └── charts.html         (图表展示)
```

#### 方案C: 子域名部署
```
www.ptqmt.com              (主网站)
data.ptqmt.com             (EasyXT数据服务)
admin.ptqmt.com            (EasyXT管理后台)
```

## 🛠️ 详细部署步骤

### 第一阶段: 环境准备 (主网站搭建完成后执行)

#### 1. 服务器环境检查
```bash
# 检查系统资源
free -h                    # 查看内存使用
df -h                      # 查看磁盘空间
netstat -tlnp             # 查看端口占用
systemctl status nginx    # 检查Nginx状态 (如果使用)
```

#### 2. 安装必要软件
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python 3.8+
sudo apt install python3.8 python3.8-venv python3-pip -y

# 安装Redis (数据缓存)
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 安装Docker (可选，推荐)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 第二阶段: EasyXT系统部署

#### 1. 创建部署目录
```bash
# 在用户目录下创建EasyXT目录
cd /home/your_username
mkdir easyxt-system
cd easyxt-system

# 创建必要的子目录
mkdir -p {config,logs,data,backup}
```

#### 2. 上传EasyXT代码
```bash
# 方法1: 使用git (推荐)
git clone https://github.com/your-repo/easyxt-realtime-data.git
cd easyxt-realtime-data

# 方法2: 直接上传文件
# 将本地的miniqmt扩展文件夹上传到服务器
scp -r ./miniqmt扩展 username@your-server-ip:/home/username/easyxt-system/
```

#### 3. 配置系统环境
```bash
# 创建Python虚拟环境
python3 -m venv easyxt-env
source easyxt-env/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp deployment/config/production.json config/
cp deployment/config/log_config.json config/
```

### 第三阶段: 配置文件调整

#### 1. 生产环境配置 (config/production.json)
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "debug": false,
    "workers": 2
  },
  "database": {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0
  },
  "data_sources": {
    "tdx": {
      "enabled": true,
      "timeout": 30
    },
    "ths": {
      "enabled": true,
      "timeout": 30
    },
    "eastmoney": {
      "enabled": true,
      "timeout": 30
    }
  },
  "cache": {
    "ttl": 300,
    "max_size": 1000
  },
  "logging": {
    "level": "INFO",
    "file": "/home/username/easyxt-system/logs/easyxt.log"
  }
}
```

#### 2. Nginx配置 (如果使用Nginx)
```nginx
# /etc/nginx/sites-available/ptqmt.com
server {
    listen 80;
    server_name www.ptqmt.com ptqmt.com;
    
    # 主网站静态文件
    location / {
        root /var/www/ptqmt.com;
        index index.html index.htm;
        try_files $uri $uri/ =404;
    }
    
    # EasyXT API代理
    location /api/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket代理
    location /ws/ {
        proxy_pass http://localhost:8080/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# EasyXT管理后台 (可选)
server {
    listen 8081;
    server_name admin.ptqmt.com;
    
    location / {
        proxy_pass http://localhost:8082/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 第四阶段: 启动服务

#### 1. 使用Docker部署 (推荐)
```bash
# 进入部署目录
cd /home/username/easyxt-system/deployment

# 修改docker-compose.yml中的配置
nano docker-compose.yml

# 启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps
docker-compose logs -f easyxt-api
```

#### 2. 直接启动 (备选方案)
```bash
# 激活虚拟环境
source easyxt-env/bin/activate

# 启动EasyXT服务
cd /home/username/easyxt-system
python -m easy_xt.realtime_data.api_server --config config/production.json

# 使用systemd管理服务 (推荐)
sudo nano /etc/systemd/system/easyxt.service
```

#### 3. Systemd服务配置
```ini
[Unit]
Description=EasyXT Realtime Data Service
After=network.target redis.service

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/easyxt-system
Environment=PATH=/home/username/easyxt-system/easyxt-env/bin
ExecStart=/home/username/easyxt-system/easyxt-env/bin/python -m easy_xt.realtime_data.api_server --config config/production.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable easyxt
sudo systemctl start easyxt
sudo systemctl status easyxt
```

## 🌐 网站集成示例

### 1. 主网站调用EasyXT数据
```html
<!-- www.ptqmt.com/data/realtime.html -->
<!DOCTYPE html>
<html>
<head>
    <title>实时行情 - PTQMT</title>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
</head>
<body>
    <h1>实时股票行情</h1>
    <div id="stock-data"></div>
    
    <script>
        // 调用EasyXT API获取数据
        async function loadStockData() {
            try {
                const response = await axios.get('/api/stocks/realtime');
                const data = response.data;
                document.getElementById('stock-data').innerHTML = 
                    JSON.stringify(data, null, 2);
            } catch (error) {
                console.error('获取数据失败:', error);
            }
        }
        
        // 页面加载时获取数据
        loadStockData();
        
        // 每30秒更新一次数据
        setInterval(loadStockData, 30000);
    </script>
</body>
</html>
```

### 2. WebSocket实时推送
```javascript
// 实时数据推送
const ws = new WebSocket('ws://www.ptqmt.com/ws/realtime');

ws.onopen = function(event) {
    console.log('WebSocket连接已建立');
    // 订阅股票数据
    ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: ['000001', '000002', '600000']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到实时数据:', data);
    // 更新页面显示
    updateStockDisplay(data);
};

ws.onclose = function(event) {
    console.log('WebSocket连接已关闭');
    // 尝试重连
    setTimeout(() => {
        location.reload();
    }, 5000);
};
```

## 📊 资源使用评估

### 服务器资源分配
```
总资源: 2核CPU, 2GB内存, 50GB硬盘, 3M带宽

建议分配:
├── 主网站 (www.ptqmt.com)
│   ├── CPU: 0.5核
│   ├── 内存: 512MB
│   └── 硬盘: 10GB
├── EasyXT系统
│   ├── CPU: 1核
│   ├── 内存: 1GB
│   └── 硬盘: 20GB (包含日志和缓存)
├── Redis缓存
│   ├── CPU: 0.2核
│   ├── 内存: 256MB
│   └── 硬盘: 5GB
└── 系统预留
    ├── CPU: 0.3核
    ├── 内存: 256MB
    └── 硬盘: 15GB
```

### 性能优化建议
1. **启用Gzip压缩** - 减少带宽使用
2. **配置CDN** - 加速静态资源加载
3. **数据缓存策略** - 减少API调用频率
4. **日志轮转** - 控制日志文件大小
5. **监控告警** - 及时发现性能问题

## 🔧 运维管理

### 1. 日常监控命令
```bash
# 查看EasyXT服务状态
sudo systemctl status easyxt

# 查看服务日志
sudo journalctl -u easyxt -f

# 查看应用日志
tail -f /home/username/easyxt-system/logs/easyxt.log

# 查看系统资源使用
htop
df -h
free -h

# 查看网络连接
netstat -tlnp | grep :8080
```

### 2. 备份策略
```bash
# 创建备份脚本
nano /home/username/backup_easyxt.sh

#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/username/backup"
SOURCE_DIR="/home/username/easyxt-system"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份配置文件
tar -czf $BACKUP_DIR/easyxt_config_$DATE.tar.gz $SOURCE_DIR/config/

# 备份日志文件 (最近7天)
find $SOURCE_DIR/logs/ -name "*.log" -mtime -7 | tar -czf $BACKUP_DIR/easyxt_logs_$DATE.tar.gz -T -

# 清理30天前的备份
find $BACKUP_DIR -name "easyxt_*" -mtime +30 -delete

echo "备份完成: $DATE"
```

```bash
# 设置定时备份
chmod +x /home/username/backup_easyxt.sh
crontab -e

# 每天凌晨2点备份
0 2 * * * /home/username/backup_easyxt.sh
```

### 3. 故障排查指南

#### 常见问题及解决方案

**问题1: EasyXT服务无法启动**
```bash
# 检查端口占用
sudo netstat -tlnp | grep :8080

# 检查配置文件
python -c "import json; json.load(open('config/production.json'))"

# 检查依赖
source easyxt-env/bin/activate
pip list
```

**问题2: 数据获取失败**
```bash
# 检查网络连接
curl -I https://quote.eastmoney.com
ping www.10jqka.com.cn

# 检查Redis连接
redis-cli ping

# 查看详细错误日志
grep ERROR /home/username/easyxt-system/logs/easyxt.log
```

**问题3: 内存使用过高**
```bash
# 查看进程内存使用
ps aux | grep python | grep easyxt

# 重启服务释放内存
sudo systemctl restart easyxt

# 调整缓存配置
nano config/production.json
# 减少cache.max_size值
```

## 📅 部署时间规划

### 建议部署时机
1. **主网站稳定运行后** - 确保基础环境正常
2. **服务器资源充足时** - 避免影响主网站性能
3. **业务需求明确时** - 确定具体的数据展示需求

### 部署步骤时间估算
- **环境准备**: 1-2小时
- **代码部署**: 30分钟
- **配置调试**: 1-2小时
- **集成测试**: 1小时
- **性能优化**: 1-2小时
- **总计**: 4.5-7.5小时

## 🎯 集成效果预期

### 用户体验提升
1. **实时数据展示** - 网站提供实时金融数据
2. **专业形象** - 展示技术实力和专业性
3. **功能丰富** - 从静态网站升级为动态数据平台

### 技术能力展示
1. **API服务能力** - 提供标准化数据接口
2. **实时推送技术** - WebSocket实时通信
3. **系统集成能力** - 多系统协同工作

### 商业价值实现
1. **数据服务** - 可对外提供数据API服务
2. **技术咨询** - 展示量化交易技术能力
3. **产品展示** - 为潜在客户提供技术演示

## 📞 技术支持

### 部署前准备清单
- [ ] 主网站www.ptqmt.com已正常运行
- [ ] 服务器资源使用率 < 50%
- [ ] 备份了现有网站数据
- [ ] 准备了EasyXT系统代码
- [ ] 规划了端口和域名使用

### 联系方式
- **技术文档**: 参考本项目的详细文档
- **问题排查**: 查看日志文件和错误信息
- **性能监控**: 使用系统自带的监控功能

---

## 💡 重要提醒

1. **先完成主网站** - 确保www.ptqmt.com稳定运行后再部署EasyXT
2. **资源监控** - 密切关注服务器资源使用情况
3. **备份重要** - 部署前务必备份现有数据
4. **逐步集成** - 建议先独立运行，再逐步集成到主网站
5. **性能测试** - 部署后进行充分的性能测试

这个详细指南将帮助您在合适的时机顺利部署EasyXT系统，并与您的主网站www.ptqmt.com完美集成！🚀