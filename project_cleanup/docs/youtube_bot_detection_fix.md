# YouTube "Sign in to confirm you're not a bot" 错误解决指南

## 🤖 错误说明

当您看到以下错误时：
```
ERROR: [youtube] VIDEO_ID: Sign in to confirm you're not a bot. 
Use --cookies-from-browser or --cookies for the authentication.
```

这表示YouTube检测到了自动化行为，要求身份验证以确认不是机器人。

## 🔍 根本原因

1. **YouTube反机器人检测升级**：YouTube加强了对自动化工具的检测
2. **PO Token要求**：YouTube正在逐步强制使用"PO Token"
3. **Cookies过期或无效**：现有cookies可能已过期或格式不正确
4. **IP地址被标记**：频繁下载导致IP被YouTube标记

## 🛠️ 官方推荐解决方案

### 方案1：正确导出YouTube Cookies（推荐）

根据yt-dlp官方文档，YouTube会频繁轮换cookies。需要使用特殊方法：

#### 步骤：
1. **打开新的隐私浏览/无痕窗口**
2. **在该窗口登录YouTube**
3. **在同一个标签页中，导航到 `https://www.youtube.com/robots.txt`**
4. **导出cookies**：
   - 使用EditThisCookie扩展
   - 选择"Export" → "Netscape HTTP Cookie File"
5. **立即关闭隐私浏览窗口**

#### 关键点：
- ✅ 必须使用隐私浏览窗口
- ✅ 必须访问robots.txt页面
- ✅ 导出后立即关闭窗口
- ✅ 30分钟内使用最有效

### 方案2：使用--cookies-from-browser（推荐）

直接从浏览器提取cookies：
```bash
yt-dlp --cookies-from-browser chrome "VIDEO_URL"
```

支持的浏览器：
- `chrome` - Google Chrome
- `firefox` - Mozilla Firefox
- `edge` - Microsoft Edge
- `safari` - Safari (macOS)

### 方案3：处理Cloudflare相关403错误

如果遇到HTTP 403错误：

1. **刷新cookies**（30分钟内有效）
2. **获取User-Agent字符串**：
   - 在浏览器中搜索"my user-agent"
   - 或访问 `chrome://version` (Chrome) / `about:support` (Firefox)
3. **使用完整命令**：
```bash
yt-dlp --user-agent "完整的User-Agent字符串" --cookies-from-browser firefox "VIDEO_URL"
```

## 🔧 在本项目中的应用

### 1. 更新Cookies
访问Web界面的Cookies管理页面：
- 选择YouTube网站
- 按照上述方法导出cookies
- 上传或粘贴cookies内容

### 2. 使用命令行工具
```bash
# 检查当前cookies状态
python setup_youtube_cookies.py check

# 创建新的cookies模板
python setup_youtube_cookies.py setup
```

### 3. 验证修复
- 使用cookies页面的"测试"功能
- 重新尝试下载视频
- 检查日志中是否还有机器人检测错误

## ⚠️ 重要注意事项

### 账户安全
- 🚨 使用账户下载可能导致账户被封（临时或永久）
- 💡 建议使用备用账户进行下载
- 🔄 避免频繁大量下载

### 技术限制
- 📊 访客会话限制：~300视频/小时
- 👤 账户会话限制：~2000视频/小时
- ⏱️ 建议在下载间添加5-10秒延迟

### 长期解决方案
- 🔄 定期更新cookies（建议每周）
- 📱 考虑使用多个账户轮换
- 🛡️ 监控下载日志，及时发现问题

## 🚀 高级解决方案

### PO Token（如果上述方法无效）
如果cookies方法仍然无效，可能需要PO Token：
- 参考yt-dlp官方的[PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- 建议使用`mweb`客户端配合PO Token

### 代理和IP轮换
如果IP被标记：
- 使用VPN或代理服务
- 更换网络环境
- 等待一段时间后重试

## 📞 获取帮助

如果问题持续存在：
1. 检查yt-dlp是否为最新版本
2. 查看[yt-dlp官方Issues](https://github.com/yt-dlp/yt-dlp/issues)
3. 确认cookies导出方法正确
4. 考虑使用PO Token方案

---

**最后更新**：2025年6月7日  
**基于**：yt-dlp官方文档和最新GitHub Issues
