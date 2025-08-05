#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('OlaMoMa/src/OlaMoMa')

from app import OllamaManager

def test_parsing():
    """测试数据解析"""
    try:
        manager = OllamaManager()
        
        # 测试获取模型列表
        print("正在获取模型列表...")
        models = manager.list_models()
        print(f"找到 {len(models)} 个模型")
        
        if not models:
            print("没有找到可用的模型")
            return
        
        # 打印第一个模型的信息来调试
        print(f"\n第一个模型的数据类型: {type(models[0])}")
        print(f"第一个模型的内容: {models[0]}")
        
        if isinstance(models[0], dict):
            print("\n前5个模型的详细信息:")
            for i, model in enumerate(models[:5]):
                print(f"模型 {i+1}:")
                print(f"  名称: {model['name']}")
                print(f"  标签: {model['tag']}")
                print(f"  ID: {model.get('id', 'N/A')}")
                print(f"  大小: {model['size']}")
                print(f"  修改时间: {model['modified_date']}")
                print(f"  完整名称: {model['full_name']}")
                print()
        else:
            print("\n前5个模型（字符串格式）:")
            for i, model in enumerate(models[:5]):
                print(f"模型 {i+1}: {model}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parsing() 