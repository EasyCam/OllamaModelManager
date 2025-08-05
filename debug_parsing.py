#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import re

def debug_parsing():
    """调试数据解析"""
    try:
        # 直接运行 ollama list 命令
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, shell=False, encoding='utf-8', timeout=10)
        
        print("ollama list 原始输出:")
        print(result.stdout)
        print("\n" + "="*50 + "\n")
        
        # 测试正则表达式
        pattern = r'^([a-zA-Z0-9_./-]+):([a-zA-Z0-9_.-]+)\s+([a-f0-9]+)\s+([0-9.]+\s*[KMG]?B?)\s+(.+)$'
        
        print("测试正则表达式匹配:")
        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line or line.startswith('NAME'):
                continue
            
            print(f"原始行: '{line}'")
            match = re.match(pattern, line)
            if match:
                print(f"✅ 匹配成功!")
                print(f"  模型名: {match.group(1)}")
                print(f"  标签: {match.group(2)}")
                print(f"  ID: {match.group(3)}")
                print(f"  大小: {match.group(4)}")
                print(f"  日期: {match.group(5)}")
            else:
                print(f"❌ 匹配失败")
            print()
            
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_parsing() 