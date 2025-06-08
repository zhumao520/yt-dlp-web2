#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立即修复损坏的 Cookies 文件
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_netscape_cookies_file(file_path):
    """修复单个 Netscape cookies 文件"""
    try:
        print(f"🔧 修复文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        fixed_lines = []
        fixed_count = 0
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # 保留注释和空行
            if not line or line.startswith('#'):
                fixed_lines.append(line)
                continue
            
            parts = line.split('\t')
            if len(parts) >= 7:
                domain = parts[0]
                domain_specified = parts[1]
                
                # 修复 domain_specified 字段
                if domain.startswith('.') and domain_specified == 'FALSE':
                    print(f"  修复第{line_num}行: {domain} domain_specified FALSE -> TRUE")
                    parts[1] = 'TRUE'
                    fixed_count += 1
                elif not domain.startswith('.') and domain_specified == 'TRUE':
                    print(f"  修复第{line_num}行: {domain} domain_specified TRUE -> FALSE")
                    parts[1] = 'FALSE'
                    fixed_count += 1
                
                fixed_lines.append('\t'.join(parts))
            else:
                print(f"  跳过第{line_num}行: 格式不正确")
                fixed_lines.append(line)
        
        if fixed_count > 0:
            # 备份原文件
            backup_path = f"{file_path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  📄 原文件备份到: {backup_path}")
            
            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            
            print(f"  ✅ 修复完成，共修复 {fixed_count} 行")
        else:
            print(f"  ℹ️ 文件格式正确，无需修复")
        
        return True, fixed_count
        
    except Exception as e:
        print(f"  ❌ 修复失败: {e}")
        return False, 0

def main():
    """主函数"""
    print("🚀 开始修复 Cookies 文件...")
    print("=" * 50)
    
    # 查找可能的 cookies 目录
    possible_dirs = [
        '/app/data/cookies',
        './data/cookies',
        './cookies',
        '/app/cookies'
    ]
    
    cookies_dir = None
    for dir_path in possible_dirs:
        if Path(dir_path).exists():
            cookies_dir = Path(dir_path)
            break
    
    if not cookies_dir:
        print("❌ 未找到 cookies 目录")
        return False
    
    print(f"📁 Cookies 目录: {cookies_dir}")
    
    # 查找所有 .txt 文件（临时 Netscape 格式文件）
    txt_files = list(cookies_dir.glob('*_temp.txt'))
    
    if not txt_files:
        print("ℹ️ 未找到需要修复的临时 cookies 文件")
        return True
    
    print(f"🔍 找到 {len(txt_files)} 个临时 cookies 文件")
    
    total_fixed = 0
    success_count = 0
    
    for txt_file in txt_files:
        success, fixed_count = fix_netscape_cookies_file(txt_file)
        if success:
            success_count += 1
            total_fixed += fixed_count
    
    print("\n" + "=" * 50)
    print(f"✅ 修复完成！")
    print(f"📊 处理文件: {len(txt_files)}")
    print(f"📊 成功修复: {success_count}")
    print(f"📊 修复行数: {total_fixed}")
    
    if total_fixed > 0:
        print("\n💡 建议重启应用以使修复生效")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
