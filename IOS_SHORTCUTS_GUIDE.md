# 📱 iOS快捷指令集成指南

## 🎯 功能概述

为iOS用户提供便捷的视频下载快捷指令，支持从Safari、YouTube、TikTok等应用直接分享链接到下载服务。

## 🔧 API端点

### **1. 下载接口**
```http
POST /api/shortcuts/download
```

**支持的数据格式**：
- JSON (`application/json`)
- 表单数据 (`application/x-www-form-urlencoded`)
- URL参数 (`?url=...&quality=...`)

**请求参数**：
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "quality": "medium",
  "audio_only": false,
  "api_key": "your_api_key_here"
}
```

**或使用用户名密码**：
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "quality": "medium", 
  "audio_only": false,
  "username": "your_username",
  "password": "your_password"
}
```

**响应**：
```json
{
  "success": true,
  "message": "下载已开始",
  "download_id": "uuid-string",
  "status_url": "/api/shortcuts/status/uuid-string"
}
```

### **2. 状态查询**
```http
GET /api/shortcuts/status/{download_id}
```

**响应**：
```json
{
  "id": "uuid-string",
  "status": "completed",
  "progress": 100,
  "title": "视频标题",
  "filename": "video.mp4",
  "file_size": 12345678,
  "download_url": "/api/shortcuts/file/video.mp4",
  "completed": true
}
```

### **3. 文件下载**
```http
GET /api/shortcuts/file/{filename}
```

直接返回文件内容，支持断点续传。

### **4. 服务信息**
```http
GET /api/shortcuts/info
```

获取服务基本信息和支持的功能。

## 🔑 认证方式

### **方式1: API密钥（推荐）**
1. 登录Web界面
2. 进入设置页面
3. 生成API密钥
4. 在快捷指令中使用API密钥

### **方式2: 用户名密码**
直接在快捷指令中提供用户名和密码

## 📲 iOS快捷指令配置

### **基础下载快捷指令**

#### **步骤1: 创建快捷指令**
1. 打开iOS"快捷指令"应用
2. 点击"+"创建新快捷指令
3. 添加以下操作：

#### **步骤2: 获取输入**
```
操作: 获取剪贴板
或
操作: 从输入获取URL
```

#### **步骤3: 发送下载请求**
```
操作: 获取URL内容
方法: POST
URL: http://your-server:8080/api/shortcuts/download
请求体: JSON

{
  "url": [剪贴板内容],
  "quality": "medium",
  "api_key": "your_api_key_here"
}
```

#### **步骤4: 解析响应**
```
操作: 从输入获取值
获取: download_id
```

#### **步骤5: 等待下载完成**
```
操作: 重复
次数: 30

  操作: 获取URL内容
  方法: GET
  URL: http://your-server:8080/api/shortcuts/status/[download_id]
  
  操作: 从输入获取值
  获取: status
  
  操作: 如果
  条件: status 等于 "completed"
    操作: 退出快捷指令
  否则
    操作: 等待
    秒数: 2
```

#### **步骤6: 下载文件**
```
操作: 从输入获取值
获取: download_url

操作: 获取URL内容
方法: GET
URL: http://your-server:8080[download_url]

操作: 存储到文件
位置: iCloud Drive/Downloads/
```

### **高级快捷指令功能**

#### **1. 质量选择**
```
操作: 从菜单中选择
选项: 
  - 最高质量 (best)
  - 中等质量 (medium) 
  - 低质量 (low)

操作: 设置变量
名称: selected_quality
值: [菜单结果]
```

#### **2. 音频提取**
```
操作: 询问输入
提示: 是否只下载音频？
输入类型: 是或否

操作: 设置变量
名称: audio_only
值: [询问结果]
```

#### **3. 进度通知**
```
操作: 显示通知
标题: 下载开始
内容: 正在下载视频...

操作: 重复 (在状态检查循环中)
  操作: 显示通知
  标题: 下载进度
  内容: [progress]%
```

## 🔧 高级配置

### **自定义服务器地址**
在快捷指令中添加文本操作：
```
操作: 文本
内容: http://your-server:8080

操作: 设置变量
名称: server_url
```

### **错误处理**
```
操作: 如果
条件: status 等于 "failed"
  操作: 显示通知
  标题: 下载失败
  内容: [error_message]
  
  操作: 退出快捷指令
```

### **文件命名**
```
操作: 从输入获取值
获取: title

操作: 替换文本
查找: [特殊字符]
替换为: _

操作: 设置变量
名称: safe_filename
```

## 📋 快捷指令模板

### **模板1: 简单下载**
- 从剪贴板获取URL
- 使用默认质量下载
- 保存到文件应用

### **模板2: 交互式下载**
- 选择质量
- 选择音频/视频
- 显示下载进度
- 自定义保存位置

### **模板3: 批量下载**
- 从文本文件读取URL列表
- 逐个下载
- 显示总体进度

## 🎯 使用场景

### **1. Safari浏览器**
1. 浏览视频网站
2. 点击分享按钮
3. 选择"快捷指令"
4. 选择下载快捷指令

### **2. YouTube应用**
1. 打开视频
2. 点击分享
3. 复制链接
4. 运行快捷指令

### **3. 社交媒体**
1. 在TikTok/Instagram等应用中
2. 分享视频链接
3. 自动触发下载

## 🔒 安全注意事项

### **API密钥安全**
- 定期更换API密钥
- 不要在公共场所分享快捷指令
- 使用HTTPS连接

### **网络安全**
- 确保服务器使用HTTPS
- 验证下载的文件来源
- 注意版权问题

## 🎉 完整示例

### **一键下载快捷指令**
```
1. 获取剪贴板
2. 设置变量 "url" = [剪贴板]
3. 获取URL内容
   - 方法: POST
   - URL: http://your-server:8080/api/shortcuts/download
   - JSON: {"url": "[url]", "quality": "medium", "api_key": "your_key"}
4. 从输入获取值 "download_id"
5. 重复30次:
   - 获取状态
   - 如果完成则退出
   - 否则等待2秒
6. 获取文件URL
7. 下载文件到iCloud Drive
8. 显示完成通知
```

## 📱 分享快捷指令

创建完成后，可以通过以下方式分享：
1. 导出为iCloud链接
2. 生成二维码
3. AirDrop分享给其他iOS用户

**现在您可以在iOS设备上轻松下载视频了！** 🚀
