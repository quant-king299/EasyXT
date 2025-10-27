# 🚀 EasyXT部署快速参考 - PTQMT集成

## 📋 一句话总结
**EasyXT是一个独立的数据服务系统，运行在8080端口，为您的主网站www.ptqmt.com提供实时金融数据API服务。**

## 🔗 系统关系
```
www.ptqmt.com (端口80) ←→ 您的主网站
localhost:8080         ←→ EasyXT数据API服务
```

## ⚡ 快速部署命令

### 1. 环境准备 (一次性)
```bash
# 安装依赖
sudo apt update
sudo apt install python3.8 python3-pip redis-server docker.io -y

# 启动Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 2. 部署EasyXT (主网站完成后执行)
```bash
# 创建目录
mkdir ~/easyxt-system && cd ~/easyxt-system

# 上传代码 (将您的miniqmt扩展文件夹上传到这里)
# scp -r ./miniqmt扩展 username@server:/home/username/easyxt-system/

# 安装Python依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动服务
python -m easy_xt.realtime_data.api_server --port 8080
```

### 3. Nginx配置 (集成到主网站)
```nginx
# 在您的www.ptqmt.com配置中添加:
location /api/ {
    proxy_pass http://localhost:8080/;
}
```

## 📊 资源使用
- **CPU**: 约1核 (50%使用率)
- **内存**: 约1GB
- **硬盘**: 约20GB (包含日志)
- **端口**: 8080 (内部使用，不对外开放)

## 🌐 访问方式
- **主网站**: http://www.ptqmt.com (不变)
- **数据API**: http://www.ptqmt.com/api/stocks/realtime
- **WebSocket**: ws://www.ptqmt.com/ws/realtime

## 🔧 常用命令
```bash
# 查看服务状态
ps aux | grep easyxt

# 查看日志
tail -f ~/easyxt-system/logs/easyxt.log

# 重启服务
pkill -f easyxt
cd ~/easyxt-system && source venv/bin/activate
python -m easy_xt.realtime_data.api_server --port 8080 &

# 查看资源使用
htop
df -h
```

## ⚠️ 重要提醒
1. **先完成主网站再部署EasyXT**
2. **EasyXT不会影响主网站运行**
3. **可以随时启动/停止EasyXT服务**
4. **建议在服务器资源使用率<50%时部署**

## 📞 如果忘记了
1. 查看这个文件: `PTQMT_DEPLOYMENT_GUIDE.md` (详细版)
2. 查看项目文档: `PROJECT_COMPLETION_SUMMARY.md`
3. 查看部署目录: `~/easyxt-system/deployment/docs/`

---
**记住**: EasyXT是您网站的数据服务后台，让www.ptqmt.com具备实时金融数据展示能力！🎯