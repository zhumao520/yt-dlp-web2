# Telegram Pyrogram 配置指南

## 🎯 目标
配置Pyrogram以支持发送50MB以上的大文件到Telegram

## 📋 前提条件
- 已有Telegram账号
- 已创建Telegram Bot并获得Bot Token
- 已获得Chat ID

## 🔧 获取API ID和API Hash

### 步骤1：访问Telegram开发者平台
1. 打开浏览器访问：https://my.telegram.org
2. 使用您的手机号码登录（与Telegram账号相同）
3. 输入收到的验证码

### 步骤2：创建应用
1. 点击 "API development tools"
2. 填写应用信息：
   - **App title**: `YT-DLP Web V2`
   - **Short name**: `ytdlp-web`
   - **URL**: 留空或填写您的域名
   - **Platform**: 选择 `Desktop`
   - **Description**: `Video downloader with Telegram integration`

### 步骤3：获取API凭据
创建成功后，您会看到：
- **API ID**: 一串数字（例如：12345678）
- **API Hash**: 一串字母数字组合（例如：abcd1234efgh5678ijkl9012mnop3456）

⚠️ **重要**：请妥善保管这些信息，不要泄露给他人！

## 🔧 在系统中配置

### 方法1：通过Web界面配置
1. 访问系统的Telegram配置页面：`/telegram`
2. 填写以下信息：
   - **Bot Token**: 您的机器人令牌
   - **Chat ID**: 您的聊天ID
   - **API ID**: 从my.telegram.org获取的API ID
   - **API Hash**: 从my.telegram.org获取的API Hash
3. 点击"保存配置"
4. 点击"测试连接"验证配置

### 方法2：通过配置文件
编辑配置文件或数据库，添加：
```json
{
  "enabled": true,
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "api_id": 12345678,
  "api_hash": "your_api_hash_here",
  "push_mode": "file",
  "file_size_limit": 50
}
```

## 🧪 测试配置

### 测试步骤
1. 保存配置后，点击"测试连接"
2. 检查测试结果：
   - ✅ **Bot API**: 基础消息发送
   - ✅ **Pyrogram**: 大文件发送支持

### 预期结果
- 您应该收到两条测试消息：
  1. "🧪 YT-DLP Web V2 连接测试" (Bot API)
  2. "🔧 Pyrogram连接测试" (Pyrogram)

## 📤 文件发送逻辑

配置完成后，系统会自动根据文件大小选择发送方式：

| 文件大小 | 发送方式 | 说明 |
|---------|---------|------|
| ≤ 50MB | Bot API | 快速发送，无需额外配置 |
| > 50MB | Pyrogram | 支持大文件，需要API ID/Hash |

## ⚠️ 注意事项

### 安全性
- 🔒 API ID和API Hash是敏感信息，请妥善保管
- 🚫 不要在公共场所或代码中暴露这些信息
- 🔄 如果泄露，请立即在my.telegram.org重新生成

### 限制
- 📊 Telegram文件大小限制：最大2GB
- ⏱️ 大文件上传可能需要较长时间
- 🌐 需要稳定的网络连接

### 故障排除
如果Pyrogram连接失败：
1. 检查API ID和API Hash是否正确
2. 确认网络连接正常
3. 查看系统日志获取详细错误信息
4. 尝试重新生成API凭据

## 🎉 完成
配置完成后，您就可以：
- ✅ 发送任意大小的文件到Telegram
- ✅ 自动根据文件大小选择最佳发送方式
- ✅ 享受无缝的大文件推送体验

---

**需要帮助？**
- 查看系统日志获取详细错误信息
- 确认所有配置信息正确无误
- 测试网络连接和Telegram服务可用性
