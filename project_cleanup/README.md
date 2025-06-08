# 项目清理文件夹

这个文件夹包含了从主项目中移除的文件，用于保持主项目的整洁。

## 📁 文件夹结构

### 📚 docs/
包含项目文档和指南：
- `DEPLOYMENT_CHECKLIST.md` - 部署检查清单
- `FEATHER_ICONS_FIX.md` - Feather图标修复指南
- `GITHUB_ACTIONS_FIX.md` - GitHub Actions修复指南
- `PROJECT_STATUS.md` - 项目状态文档
- `cookies_format_guide.md` - Cookies格式指南
- `telegram_pyrogram_setup_guide.md` - Telegram Pyrogram配置指南
- `youtube_bot_detection_fix.md` - YouTube机器人检测修复指南

### 🔧 scripts/
包含辅助脚本和工具：
- `check_dependencies.py` - 依赖检查脚本
- `cookies_converter.py` - Cookies转换工具
- `fix_common_issues.py` - 常见问题修复脚本
- `fix_cookies_now.py` - Cookies修复工具
- `setup_youtube_cookies.py` - YouTube Cookies设置工具
- `test_startup.py` - 启动测试脚本
- `test_system.py` - 系统测试脚本
- `web_update_ytdlp.py` - yt-dlp更新脚本

### 🧪 tests_and_debug/
包含测试文件和调试工具：
- `test_icons.html` - 图标测试页面
- `tests/` - 单元测试文件夹

### 💾 cache_backup/
包含备份的缓存文件：
- `ytdlp_bot.session` - Pyrogram会话文件备份
- `ytdlp_bot.session-journal` - Pyrogram会话日志备份

## 📝 说明

这些文件在开发过程中很有用，但不是运行应用程序的必需文件。它们被移动到这里以：

1. **保持主项目整洁** - 只保留运行必需的文件
2. **便于GitHub上传** - 减少仓库大小
3. **保留有用信息** - 文档和工具仍然可用
4. **备份重要数据** - 缓存文件得到保留

## 🔄 如何使用

如果需要使用这些文件：
1. 将需要的文件复制回主项目目录
2. 或者直接在此文件夹中运行脚本
3. 文档可以直接查看

## ⚠️ 注意

- 这个文件夹已被添加到 `.gitignore` 中
- 上传到GitHub时不会包含这些文件
- 如果需要在GitHub上保留某些文档，请将其移回主目录
