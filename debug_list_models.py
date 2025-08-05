#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('OlaMoMa/src/OlaMoMa')

from app import OllamaManager

def debug_list_models():
    """调试list_models函数"""
    try:
        manager = OllamaManager()
        
        print("调用 list_models() 函数...")
        models = manager.list_models()
        
        print(f"返回值类型: {type(models)}")
        print(f"返回值长度: {len(models)}")
        
        if models:
            print(f"第一个元素类型: {type(models[0])}")
            print(f"第一个元素内容: {models[0]}")
            
            if isinstance(models[0], dict):
                print("\n前3个模型的详细信息:")
                for i, model in enumerate(models[:3]):
                    print(f"模型 {i+1}:")
                    for key, value in model.items():
                        print(f"  {key}: {value}")
                    print()
            else:
                print("\n前3个模型（字符串格式）:")
                for i, model in enumerate(models[:3]):
                    print(f"模型 {i+1}: {model}")
        else:
            print("没有返回任何模型")
            
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_list_models() 