"""A graphical tool designed to export Ollama models to GGUF format and import GGUF files back into Ollama models. It provides an intuitive user interface for managing your Ollama models, supporting both Windows and Linux operating systems.
"""
import importlib.metadata
import sys

from PySide6 import QtWidgets

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QListWidget, QLabel, QFileDialog, 
                             QMessageBox, QProgressBar, QInputDialog, QMenuBar, QMenu,
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTranslator, QLocale, QTimer
from PySide6.QtGui import QAction

class OllamaManager:
    """管理Ollama模型的类"""
    
    def __init__(self):
        self.ollama_path = self.find_ollama()
    
    def tr(self, text):
        """简单的翻译方法，实际应用中应使用更完整的国际化方案"""
        # 这里只是一个简单的占位符实现
        # 在实际应用中，需要使用 QApplication.instance().translate()
        # 或者其他更完整的国际化方案
        return text
    
    def tr_with_args(self, text, *args):
        """支持参数的翻译方法"""
        translated = self.tr(text)
        for i, arg in enumerate(args):
            translated = translated.replace(f"%{i+1}", str(arg))
        return translated
    
    def find_ollama(self):
        """查找Ollama可执行文件"""
        # 常见的Ollama安装路径
        possible_paths = [
            "ollama",
            "C:\\Program Files\\Ollama\\ollama.exe",
            "C:\\Users\\%USERNAME%\\AppData\\Local\\Ollama\\ollama.exe",
            "/usr/bin/ollama",
            "/usr/local/bin/ollama"
        ]
        
        # 尝试在PATH中查找
        import shutil
        ollama_path = shutil.which("ollama")
        if ollama_path:
            return ollama_path
            
        # 如果在PATH中找不到，则尝试常见路径
        for path in possible_paths:
            # 在Windows上，替换%USERNAME%
            if os.name == 'nt' and '%USERNAME%' in path:
                import getpass
                username = getpass.getuser()
                path = path.replace('%USERNAME%', username)
            
            if os.path.exists(path):
                return path
                
        return None
    
    def list_models(self):
        """列出所有已下载的模型，返回详细的模型信息"""
        try:
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=False, encoding='utf-8', timeout=10)
            if result.returncode != 0:
                raise Exception(f"Failed to list models: {result.stderr}")
            
            # 解析输出，提取详细的模型信息
            import re
            models = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('NAME'):  # 跳过标题行和空行
                    continue
                
                # 尝试多种格式匹配
                # 格式1: model_name:tag    size    modified_date
                # 格式2: model_name    size    modified_date
                # 格式3: model_name:tag    size
                patterns = [
                    r'^([a-zA-Z0-9_.-]+):([^\s]+)\s+([0-9.]+[KMG]?B?)\s+(.+)$',
                    r'^([a-zA-Z0-9_.-]+)\s+([0-9.]+[KMG]?B?)\s+(.+)$',
                    r'^([a-zA-Z0-9_.-]+):([^\s]+)\s+([0-9.]+[KMG]?B?)$',
                    r'^([a-zA-Z0-9_.-]+)\s+([0-9.]+[KMG]?B?)$'
                ]
                
                matched = False
                for pattern in patterns:
                    match = re.match(pattern, line)
                    if match:
                        groups = match.groups()
                        if len(groups) == 4:  # 格式1: name:tag size date
                            model_name = groups[0].strip()
                            tag = groups[1].strip()
                            size = groups[2].strip()
                            modified_date = groups[3].strip()
                        elif len(groups) == 3:  # 格式2: name size date 或 格式3: name:tag size
                            if ':' in groups[0]:  # 格式3: name:tag size
                                name_parts = groups[0].split(':', 1)
                                model_name = name_parts[0].strip()
                                tag = name_parts[1].strip()
                                size = groups[1].strip()
                                modified_date = groups[2].strip()
                            else:  # 格式2: name size date
                                model_name = groups[0].strip()
                                tag = ""
                                size = groups[1].strip()
                                modified_date = groups[2].strip()
                        elif len(groups) == 2:  # 格式4: name size
                            if ':' in groups[0]:  # name:tag size
                                name_parts = groups[0].split(':', 1)
                                model_name = name_parts[0].strip()
                                tag = name_parts[1].strip()
                                size = groups[1].strip()
                                modified_date = ""
                            else:  # name size
                                model_name = groups[0].strip()
                                tag = ""
                                size = groups[1].strip()
                                modified_date = ""
                        
                        # 创建完整的模型标识符
                        full_name = f"{model_name}:{tag}" if tag else model_name
                        
                        models.append({
                            'name': model_name,
                            'tag': tag,
                            'full_name': full_name,
                            'size': size,
                            'modified_date': modified_date
                        })
                        matched = True
                        break
                
                if not matched:
                    # 如果所有模式都不匹配，尝试简单的名称提取
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        if ':' in model_name:
                            name_parts = model_name.split(':', 1)
                            model_name = name_parts[0].strip()
                            tag = name_parts[1].strip()
                        else:
                            tag = ""
                        
                        full_name = f"{model_name}:{tag}" if tag else model_name
                        size = parts[1] if len(parts) > 1 else ""
                        modified_date = " ".join(parts[2:]) if len(parts) > 2 else ""
                        
                        models.append({
                            'name': model_name,
                            'tag': tag,
                            'full_name': full_name,
                            'size': size,
                            'modified_date': modified_date
                        })
            
            return models
        except subprocess.TimeoutExpired:
            raise Exception("Timeout while listing models")
        except Exception as e:
            raise Exception(f"Error listing models: {str(e)}")
    
    def export_model(self, model_name, export_path):
        """导出模型到指定路径"""
        if not self.ollama_path:
            raise Exception("Ollama executable not found")
        
        try:
            # 使用 ollama show --modelfile 命令获取模型文件内容
            cmd = [self.ollama_path, "show", "--modelfile", model_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding='utf-8')
            
            if result.returncode != 0:
                raise Exception(f"Failed to get model file: {result.stderr}")
            
            # 解析 Modelfile 内容找到实际的模型文件路径
            modelfile_content = result.stdout
            model_file_path = None
            
            # 查找 FROM 行中的模型文件路径
            for line in modelfile_content.split('\n'):
                if line.startswith('FROM '):
                    model_file_path = line.split(' ')[1].strip()
                    break
            
            if not model_file_path:
                raise Exception("Could not find model file path")
            
            # 如果模型文件路径是相对路径，则转换为绝对路径
            if model_file_path.startswith('~'):
                model_file_path = os.path.expanduser(model_file_path)
            elif not os.path.isabs(model_file_path):
                # 假设模型文件在 Ollama 默认存储路径下
                ollama_models_dir = os.environ.get('OLLAMA_MODELS', os.path.expanduser('~/.ollama/models'))
                model_file_path = os.path.join(ollama_models_dir, 'blobs', model_file_path)
            # 如果模型文件路径已经是绝对路径，直接使用
            
            # 检查模型文件是否存在
            if not os.path.exists(model_file_path):
                raise Exception(f"Model file does not exist: {model_file_path}")
            
            # 创建导出目录
            export_dir = os.path.dirname(export_path)
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # 复制模型文件到导出路径
            import shutil
            shutil.copy2(model_file_path, export_path)
            
            # 导出Modelfile到同一目录
            modelfile_path = os.path.splitext(export_path)[0] + ".modelfile"
            with open(modelfile_path, 'w', encoding='utf-8') as f:
                f.write(modelfile_content)
            
            return True
        except Exception as e:
            raise Exception(f"Error exporting model: {str(e)}")
    
    def import_model(self, import_path, new_model_name=None):
        """从指定路径导入模型"""
        if not self.ollama_path:
            raise Exception("Ollama executable not found")
        
        # 检查Ollama服务是否运行
        try:
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=False, encoding='utf-8', timeout=10)
            if result.returncode != 0:
                raise Exception("Ollama service is not running. Please start Ollama first.")
        except subprocess.TimeoutExpired:
            raise Exception("Ollama service is not responding. Please start Ollama first.")
        except Exception as e:
            raise Exception(f"Failed to connect to Ollama service: {str(e)}")
        
        try:
            # 检查文件是否存在
            if not os.path.exists(import_path):
                raise Exception(f"File does not exist: {import_path}")
            
            # 检查文件是否为GGUF格式
            if not import_path.lower().endswith('.gguf'):
                raise Exception("File must be in GGUF format")
            
            # 获取文件的绝对路径
            import_path = os.path.abspath(import_path)
            
            # 如果没有指定模型名，使用文件名（去掉扩展名）
            if not new_model_name:
                new_model_name = os.path.splitext(os.path.basename(import_path))[0]
            
            # 验证模型名是否有效（不能包含特殊字符）
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', new_model_name):
                raise Exception("Model name can only contain letters, numbers, underscores, and hyphens")
            
            # 检查是否存在对应的Modelfile
            modelfile_path = os.path.splitext(import_path)[0] + ".modelfile"
            if os.path.exists(modelfile_path):
                # 使用现有的Modelfile，但需要修改FROM路径
                with open(modelfile_path, 'r', encoding='utf-8') as f:
                    modelfile_content = f.read()
                
                # 更新FROM路径为当前GGUF文件的路径
                lines = modelfile_content.split('\n')
                updated_lines = []
                for line in lines:
                    if line.startswith('FROM '):
                        updated_lines.append(f"FROM {import_path}")
                    else:
                        updated_lines.append(line)
                
                modelfile_content = '\n'.join(updated_lines)
            else:
                # 如果没有找到Modelfile，使用默认配置
                modelfile_content = self.create_modelfile_content(import_path, new_model_name)
            
            # 使用系统临时目录创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.modelfile', delete=False, encoding='utf-8') as f:
                f.write(modelfile_content)
                temp_modelfile = f.name
            
            try:
                # 使用ollama create命令创建模型
                cmd = [self.ollama_path, "create", new_model_name, "-f", temp_modelfile]
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding='utf-8')
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                    raise Exception(f"Failed to import model: {error_msg}")
                
                return True
            finally:
                # 清理临时文件
                if os.path.exists(temp_modelfile):
                    try:
                        os.remove(temp_modelfile)
                    except:
                        pass
                        
        except Exception as e:
            raise Exception(f"Error importing model: {str(e)}")
    
    def create_modelfile_content(self, import_path, model_name):
        """根据模型类型创建相应的Modelfile内容"""
        filename = os.path.basename(import_path).lower()
        
        # 根据文件名推测模型类型
        if any(keyword in filename for keyword in ['qwen', 'qwen2', 'qwen3']):
            return self.create_qwen_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['llama', 'llama2', 'llama3']):
            return self.create_llama_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['mistral', 'mixtral']):
            return self.create_mistral_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['gemma']):
            return self.create_gemma_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['phi', 'phi2', 'phi3']):
            return self.create_phi_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['yi', '01-yi']):
            return self.create_yi_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['deepseek']):
            return self.create_deepseek_modelfile(import_path, model_name)
        elif any(keyword in filename for keyword in ['codellama', 'code-llama']):
            return self.create_codellama_modelfile(import_path, model_name)
        else:
            # 默认配置
            return self.create_default_modelfile(import_path, model_name)
    
    def create_qwen_modelfile(self, import_path, model_name):
        """创建Qwen模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are Qwen, a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# Qwen模板
TEMPLATE "{{ if .System }}<|system|>
{{ .System }}
<|end|>

{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}
<|end|>

{{ end }}<|assistant|>
{{ .Response }}
<|end|>"

# 停止标记
STOP "<|system|>"
STOP "<|user|>"
STOP "<|assistant|>"
STOP "<|end|>"
"""
    
    def create_llama_modelfile(self, import_path, model_name):
        """创建Llama模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# Llama模板
TEMPLATE "{{ if .System }}<s>[INST] <<SYS>>
{{ .System }}
<</SYS>>

{{ .Prompt }} [/INST]{{ else }}{{ if .Prompt }}<s>[INST] {{ .Prompt }} [/INST]{{ end }}{{ end }} {{ .Response }}</s>"

# 停止标记
STOP "</s>"
STOP "[INST]"
"""
    
    def create_mistral_modelfile(self, import_path, model_name):
        """创建Mistral模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# Mistral模板
TEMPLATE "{{ if .System }}<s>[INST] {{ .System }}

{{ .Prompt }} [/INST]{{ else }}{{ if .Prompt }}<s>[INST] {{ .Prompt }} [/INST]{{ end }}{{ end }} {{ .Response }}</s>"

# 停止标记
STOP "</s>"
STOP "[INST]"
"""
    
    def create_gemma_modelfile(self, import_path, model_name):
        """创建Gemma模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# Gemma模板
TEMPLATE "{{ if .System }}<start_of_turn>user
{{ .System }}

{{ .Prompt }}<end_of_turn>
<start_of_turn>model
{{ .Response }}<end_of_turn>{{ else }}{{ if .Prompt }}<start_of_turn>user
{{ .Prompt }}<end_of_turn>
<start_of_turn>model
{{ .Response }}<end_of_turn>{{ end }}{{ end }}"

# 停止标记
STOP "<start_of_turn>"
STOP "<end_of_turn>"
"""
    
    def create_phi_modelfile(self, import_path, model_name):
        """创建Phi模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# Phi模板
TEMPLATE "{{ if .System }}<|system|>
{{ .System }}
<|end|>
{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}
<|end|>
{{ end }}<|assistant|>
{{ .Response }}
<|end|>"

# 停止标记
STOP "<|system|>"
STOP "<|user|>"
STOP "<|assistant|>"
STOP "<|end|>"
"""
    
    def create_yi_modelfile(self, import_path, model_name):
        """创建Yi模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# Yi模板
TEMPLATE "{{ if .System }}<|system|>
{{ .System }}
<|end|>

{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}
<|end|>

{{ end }}<|assistant|>
{{ .Response }}
<|end|>"

# 停止标记
STOP "<|system|>"
STOP "<|user|>"
STOP "<|assistant|>"
STOP "<|end|>"
"""
    
    def create_deepseek_modelfile(self, import_path, model_name):
        """创建DeepSeek模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# DeepSeek模板
TEMPLATE "{{ if .System }}<|system|>
{{ .System }}
<|end|>

{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}
<|end|>

{{ end }}<|assistant|>
{{ .Response }}
<|end|>"

# 停止标记
STOP "<|system|>"
STOP "<|user|>"
STOP "<|assistant|>"
STOP "<|end|>"
"""
    
    def create_codellama_modelfile(self, import_path, model_name):
        """创建CodeLlama模型的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are an expert programmer. You write clean, efficient, and well-documented code. Always provide helpful explanations for your code."

# CodeLlama模板
TEMPLATE "{{ if .System }}<s>[INST] <<SYS>>
{{ .System }}
<</SYS>>

{{ .Prompt }} [/INST]{{ else }}{{ if .Prompt }}<s>[INST] {{ .Prompt }} [/INST]{{ end }}{{ end }} {{ .Response }}</s>"

# 停止标记
STOP "</s>"
STOP "[INST]"
"""
    
    def create_default_modelfile(self, import_path, model_name):
        """创建默认的Modelfile"""
        return f"""FROM {import_path}

# 模型参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# 系统提示词
SYSTEM "You are a helpful AI assistant. You provide accurate, helpful, and safe responses to user queries."

# 通用模板
TEMPLATE "{{ if .System }}<|system|>
{{ .System }}
<|end|>

{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}
<|end|>

{{ end }}<|assistant|>
{{ .Response }}
<|end|>"

# 停止标记
STOP "<|system|>"
STOP "<|user|>"
STOP "<|assistant|>"
STOP "<|end|>"
"""

    def delete_model(self, model_name):
        """删除指定的模型"""
        if not self.ollama_path:
            raise Exception("Ollama executable not found")
        
        try:
            # 检查Ollama服务是否运行
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=False, encoding='utf-8', timeout=10)
            if result.returncode != 0:
                raise Exception("Ollama service is not running. Please start Ollama first.")
            
            # 使用 ollama rm 命令删除模型
            cmd = [self.ollama_path, "rm", model_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding='utf-8', timeout=30)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                raise Exception(f"Failed to delete model: {error_msg}")
            
            return True
        except subprocess.TimeoutExpired:
            raise Exception("Timeout while deleting model")
        except Exception as e:
            raise Exception(f"Error deleting model: {str(e)}")
    
    def update_model(self, model_name):
        """更新指定模型"""
        if not self.ollama_path:
            raise Exception("Ollama executable not found")
        
        try:
            # 检查Ollama服务是否运行
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=False, encoding='utf-8', timeout=10)
            if result.returncode != 0:
                raise Exception("Ollama service is not running. Please start Ollama first.")
            
            # 使用 ollama pull 命令更新模型
            cmd = [self.ollama_path, "pull", model_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding='utf-8', timeout=300)  # 5分钟超时
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                raise Exception(f"Failed to update model: {error_msg}")
                
            return True
        except subprocess.TimeoutExpired:
            raise Exception("Timeout while updating model")
        except Exception as e:
            raise Exception(f"Error updating model: {str(e)}")


class WorkerThread(QThread):
    """工作线程，用于执行耗时操作"""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args
        self._is_cancelled = False
    
    def cancel(self):
        """取消操作"""
        self._is_cancelled = True
    
    def run(self):
        try:
            if self._is_cancelled:
                return
                
            if self.operation == "list":
                manager = OllamaManager()
                models = manager.list_models()
                if not self._is_cancelled:
                    self.finished.emit(True, json.dumps(models))
            elif self.operation == "export":
                manager = OllamaManager()
                model_name, export_path = self.args
                manager.export_model(model_name, export_path)
                if not self._is_cancelled:
                    modelfile_path = os.path.splitext(export_path)[0] + ".modelfile"
                    message = f"Model {model_name} successfully exported to {export_path} and Modelfile to {modelfile_path}"
                    self.finished.emit(True, message)
            elif self.operation == "import":
                manager = OllamaManager()
                import_path, new_model_name = self.args
                manager.import_model(import_path, new_model_name)
                
                if not self._is_cancelled:
                    message = f"Model successfully imported from {import_path} with name {new_model_name}"
                    self.finished.emit(True, message)
            elif self.operation == "delete":
                manager = OllamaManager()
                model_name = self.args[0]
                manager.delete_model(model_name)
                if not self._is_cancelled:
                    message = f"Model {model_name} successfully deleted"
                    self.finished.emit(True, message)
            elif self.operation == "update":
                manager = OllamaManager()
                model_name = self.args[0]
                manager.update_model(model_name)
                if not self._is_cancelled:
                    message = f"Model {model_name} successfully updated"
                    self.finished.emit(True, message)
        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(False, str(e))
        finally:
            # Ensure thread is properly cleaned up
            self._is_cancelled = True


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self, language_code=None):
        super().__init__()
        self.language_code = language_code
        
        # 加载翻译文件
        self.translator = QTranslator()
        if language_code:
            locale = language_code
        else:
            locale = QLocale.system().name()
        
        # 尝试加载翻译文件
        if locale.startswith('zh'):
            # 加载中文翻译
            # 注意：这里需要有实际的翻译文件
            self.translator.load("translations/omm_zh.qm")
        else:
            # 加载英文翻译
            # 注意：这里需要有实际的翻译文件
            self.translator.load("translations/omm_en.qm")
        
        # 安装翻译器
        app = QApplication.instance()
        if app:
            app.installTranslator(self.translator)
        
        self.setWindowTitle(self.tr("Ollama Model Manager"))
        self.setGeometry(100, 100, 600, 400)
        
        self.manager = OllamaManager()
        self.worker_thread = None
        
        self.init_ui()
        
        # Use a timer to delay the initial model loading
        QTimer.singleShot(500, self.load_models)
    
    def closeEvent(self, event):
        """窗口关闭事件，确保线程正确清理"""
        if self.worker_thread and self.worker_thread.isRunning():
            try:
                self.worker_thread.finished.disconnect()
            except:
                pass
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):  # 等待最多3秒
                self.worker_thread.terminate()
                self.worker_thread.wait(1000)
        event.accept()
    
    def init_ui(self):
        """初始化用户界面"""
        # 清除现有的中央部件（如果存在）
        if self.centralWidget():
            self.centralWidget().setParent(None)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 标题
        title_label = QLabel(self.tr("Ollama Model Manager"))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 排序控件
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel(self.tr("Sort by:")))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            self.tr("Name (A-Z)"),
            self.tr("Name (Z-A)"),
            self.tr("Size (Largest First)"),
            self.tr("Size (Smallest First)"),
            self.tr("Date (Newest First)"),
            self.tr("Date (Oldest First)")
        ])
        self.sort_combo.currentIndexChanged.connect(self.sort_models)
        sort_layout.addWidget(self.sort_combo)
        
        sort_layout.addStretch()
        
        # 搜索控件
        sort_layout.addWidget(QLabel(self.tr("Search:")))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Enter model name to search..."))
        self.search_input.textChanged.connect(self.filter_models)
        sort_layout.addWidget(self.search_input)
        
        # 清除搜索按钮
        self.clear_search_button = QPushButton(self.tr("Clear"))
        self.clear_search_button.clicked.connect(self.clear_search)
        self.clear_search_button.setMaximumWidth(60)
        sort_layout.addWidget(self.clear_search_button)
        
        layout.addLayout(sort_layout)
        
        # 模型表格
        layout.addWidget(QLabel(self.tr("Downloaded Models:")))
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels([
            self.tr("Model Name"),
            self.tr("Tag"),
            self.tr("Size"),
            self.tr("Modified Date")
        ])
        
        # 设置表格属性
        self.model_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.model_table.setSelectionMode(QTableWidget.SingleSelection)
        self.model_table.setAlternatingRowColors(True)
        self.model_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.model_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 设置列宽
        header = self.model_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 模型名称列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Tag列自适应内容
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 大小列自适应内容
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 日期列自适应内容
        
        layout.addWidget(self.model_table)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton(self.tr("Refresh List"))
        self.refresh_button.clicked.connect(self.load_models)
        button_layout.addWidget(self.refresh_button)
        
        self.export_button = QPushButton(self.tr("Export Selected Model"))
        self.export_button.clicked.connect(self.export_model)
        button_layout.addWidget(self.export_button)
        
        self.import_button = QPushButton(self.tr("Import Model"))
        self.import_button.clicked.connect(self.import_model)
        button_layout.addWidget(self.import_button)

        self.delete_button = QPushButton(self.tr("Delete Selected Model"))
        self.delete_button.clicked.connect(self.delete_model)
        button_layout.addWidget(self.delete_button)
        
        self.update_button = QPushButton(self.tr("Update Selected Model"))
        self.update_button.clicked.connect(self.update_model)
        button_layout.addWidget(self.update_button)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel(self.tr("Ready"))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 状态栏
        self.statusBar = self.statusBar()
        self.statusBar.showMessage(self.tr("Ready - Press F5 to refresh, Ctrl+F to search"))
        
        # 存储模型数据
        self.models_data = []
        self.original_models_data = []  # 存储原始数据用于搜索
    
    def load_models(self):
        """加载模型列表"""
        # 如果已有线程在运行，先清理
        if self.worker_thread and self.worker_thread.isRunning():
            try:
                self.worker_thread.finished.disconnect()
            except:
                pass
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                self.worker_thread.terminate()
                self.worker_thread.wait(500)
        
        self.status_label.setText(self.tr("Loading model list..."))
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("list")
        self.worker_thread.finished.connect(self.on_models_loaded)
        self.worker_thread.start()
    
    def on_models_loaded(self, success, data):
        """模型列表加载完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            models = json.loads(data)
            self.models_data = models  # 存储模型数据用于排序
            self.original_models_data = models # 存储原始数据用于搜索
            self.model_table.setRowCount(0)  # 清空现有行
            for model in models:
                self.add_model_to_table(model)
            self.status_label.setText(self.tr("Loaded %n models", "", len(models)))
            self.statusBar.showMessage(self.tr("Ready - %n models loaded. Press F5 to refresh, Ctrl+F to search").replace("%n", str(len(models))))
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to load model list: %1").replace("%1", data))
            self.status_label.setText(self.tr("Failed to load model list"))
            self.statusBar.showMessage(self.tr("Error loading models"))
    
    def export_model(self):
        """导出选中的模型"""
        selected_items = self.model_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a model first"))
            return
        
        # 获取选中行的模型完整名称
        row = selected_items[0].row()
        model_full_name = self.model_table.item(row, 0).data(Qt.UserRole)
        
        # 选择导出路径
        export_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Select Export Path"), f"{model_full_name}.gguf", self.tr("GGUF Files (*.gguf);;All Files (*)"))
        
        if not export_path:
            return
        
        # 如果已有线程在运行，先清理
        if self.worker_thread and self.worker_thread.isRunning():
            try:
                self.worker_thread.finished.disconnect()
            except:
                pass
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                self.worker_thread.terminate()
                self.worker_thread.wait(500)
        
        self.status_label.setText(self.tr("Exporting model %1...").replace("%1", model_full_name))
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("export", model_full_name, export_path)
        self.worker_thread.finished.connect(self.on_export_finished)
        self.worker_thread.start()
    
    def on_export_finished(self, success, message):
        """导出完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, self.tr("Success"), message)
            self.status_label.setText(self.tr("Model exported successfully"))
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Export failed: %1").replace("%1", message))
            self.status_label.setText(self.tr("Model export failed"))
    
    def import_model(self):
        """导入模型"""
        # 选择导入文件
        import_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Model File to Import"), "", self.tr("GGUF Files (*.gguf);;All Files (*)"))
        
        if not import_path:
            return
        
        # 获取文件名作为模型名
        model_name = Path(import_path).stem
        
        # 验证文件名是否包含特殊字符
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', model_name):
            # 如果文件名包含特殊字符，提示用户输入新的模型名
            new_model_name, ok = QInputDialog.getText(
                self, self.tr("Model Name"), 
                self.tr("The file name contains special characters. Please enter a valid model name:"), 
                text=model_name.replace(re.sub(r'[^a-zA-Z0-9_-]', '', model_name), ''))
            
            if not ok:
                self.status_label.setText(self.tr("Import operation cancelled"))
                return
            
            if not new_model_name:
                QMessageBox.warning(self, self.tr("Warning"), self.tr("Model name cannot be empty"))
                return
        else:
            # 询问是否需要修改模型名
            new_model_name, ok = QInputDialog.getText(
                self, self.tr("Model Name"), 
                self.tr("Please enter model name (optional):"), 
                text=model_name)
            
            # 如果用户取消输入对话框，返回
            if not ok:
                self.status_label.setText(self.tr("Import operation cancelled"))
                return
            
            # 如果用户没有输入新名称，使用默认名称
            if not new_model_name:
                new_model_name = model_name
        
        # 验证模型名是否有效
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_model_name):
            QMessageBox.warning(self, self.tr("Warning"), 
                              self.tr("Model name can only contain letters, numbers, underscores, and hyphens"))
            return
        
        # 如果已有线程在运行，先清理
        if self.worker_thread and self.worker_thread.isRunning():
            try:
                self.worker_thread.finished.disconnect()
            except:
                pass
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                self.worker_thread.terminate()
                self.worker_thread.wait(500)
        
        self.status_label.setText(self.tr("Importing model %1...").replace("%1", new_model_name))
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("import", import_path, new_model_name)
        self.worker_thread.finished.connect(self.on_import_finished)
        self.worker_thread.start()
    
    def on_import_finished(self, success, message):
        """导入完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, self.tr("Success"), message)
            self.status_label.setText(self.tr("Model imported successfully"))
            # 重新加载模型列表
            self.load_models()
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Import failed: %1").replace("%1", message))
            self.status_label.setText(self.tr("Model import failed"))
    

    def delete_model(self):
        """删除选中的模型"""
        selected_items = self.model_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a model first"))
            return
        
        # 获取选中行的模型完整名称
        row = selected_items[0].row()
        model_full_name = self.model_table.item(row, 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, self.tr("Confirm Deletion"),
            self.tr("Are you sure you want to delete the model \"%1\"?").replace("%1", model_full_name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 如果已有线程在运行，先清理
            if self.worker_thread and self.worker_thread.isRunning():
                try:
                    self.worker_thread.finished.disconnect()
                except:
                    pass
                self.worker_thread.quit()
                if not self.worker_thread.wait(1000):
                    self.worker_thread.terminate()
                    self.worker_thread.wait(500)
            
            self.status_label.setText(self.tr("Deleting model %1...").replace("%1", model_full_name))
            self.progress_bar.setVisible(True)
            
            self.worker_thread = WorkerThread("delete", model_full_name)
            self.worker_thread.finished.connect(self.on_delete_finished)
            self.worker_thread.start()
        else:
            self.status_label.setText(self.tr("Model deletion cancelled"))

    def update_model(self):
        """更新选中的模型"""
        selected_items = self.model_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a model first"))
            return
        
        # 获取选中行的模型完整名称
        row = selected_items[0].row()
        model_full_name = self.model_table.item(row, 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, self.tr("Confirm Update"),
            self.tr("Are you sure you want to update the model \"%1\"? This may take a while.").replace("%1", model_full_name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 如果已有线程在运行，先清理
            if self.worker_thread and self.worker_thread.isRunning():
                try:
                    self.worker_thread.finished.disconnect()
                except:
                    pass
                self.worker_thread.quit()
                if not self.worker_thread.wait(1000):
                    self.worker_thread.terminate()
                    self.worker_thread.wait(500)
            
            self.status_label.setText(self.tr("Updating model %1...").replace("%1", model_full_name))
            self.progress_bar.setVisible(True)
            
            self.worker_thread = WorkerThread("update", model_full_name)
            self.worker_thread.finished.connect(self.on_update_finished)
            self.worker_thread.start()
        else:
            self.status_label.setText(self.tr("Model update cancelled"))

    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 清除现有菜单
        menu_bar.clear()
        
        # 语言菜单
        lang_menu = menu_bar.addMenu(self.tr("Language"))
        
        # 中文菜单项
        cn_action = QAction("中文", self)
        cn_action.triggered.connect(lambda: self.switch_language("zh"))
        lang_menu.addAction(cn_action)
        
        # 英文菜单项
        en_action = QAction("English", self)
        en_action.triggered.connect(lambda: self.switch_language("en"))
        lang_menu.addAction(en_action)
    
    def switch_language(self, language_code):
        """切换语言"""
        # 移除旧的翻译器
        app = QApplication.instance()
        if app and hasattr(self, 'translator'):
            app.removeTranslator(self.translator)
        
        # 创建新的翻译器
        self.translator = QTranslator()
        
        # 尝试加载翻译文件
        if language_code.startswith('zh'):
            # 加载中文翻译
            # 注意：这里需要有实际的翻译文件
            self.translator.load("translations/omm_zh.qm")
        else:
            # 加载英文翻译
            # 注意：这里需要有实际的翻译文件
            self.translator.load("translations/omm_en.qm")
        
        # 安装新的翻译器
        if app:
            app.installTranslator(self.translator)
        
        # 更新语言代码
        self.language_code = language_code
        
        # 重新初始化UI以应用新的翻译
        self.init_ui()
        
        # 显示语言切换成功的消息
        # QMessageBox.information(self, self.tr("Language Switched"), 
        #                       self.tr("Language switched to %1. Changes will be applied immediately.").replace("%1", language_code))
        self.load_models()

    def parse_size(self, size_str):
        """解析大小字符串，返回字节数用于排序"""
        if not size_str:
            return 0
        
        size_str = size_str.strip().upper()
        try:
            if size_str.endswith('B'):
                size_str = size_str[:-1]
            
            if size_str.endswith('K'):
                return int(float(size_str[:-1]) * 1024)
            elif size_str.endswith('M'):
                return int(float(size_str[:-1]) * 1024 * 1024)
            elif size_str.endswith('G'):
                return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
            else:
                return int(float(size_str))
        except:
            return 0
    
    def parse_date(self, date_str):
        """解析日期字符串，返回时间戳用于排序"""
        if not date_str:
            return 0
        
        try:
            from datetime import datetime
            # 尝试解析常见的日期格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M",
                "%m/%d/%Y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt).timestamp()
                except:
                    continue
            
            # 如果所有格式都失败，返回0
            return 0
        except:
            return 0

    def sort_models(self):
        """根据选择的排序方式对模型列表进行排序"""
        sort_by = self.sort_combo.currentText()
        
        if sort_by == self.tr("Name (A-Z)"):
            self.models_data.sort(key=lambda x: x['name'].lower())
        elif sort_by == self.tr("Name (Z-A)"):
            self.models_data.sort(key=lambda x: x['name'].lower(), reverse=True)
        elif sort_by == self.tr("Size (Largest First)"):
            self.models_data.sort(key=lambda x: self.parse_size(x['size']), reverse=True)
        elif sort_by == self.tr("Size (Smallest First)"):
            self.models_data.sort(key=lambda x: self.parse_size(x['size']))
        elif sort_by == self.tr("Date (Newest First)"):
            self.models_data.sort(key=lambda x: self.parse_date(x['modified_date']), reverse=True)
        elif sort_by == self.tr("Date (Oldest First)"):
            self.models_data.sort(key=lambda x: self.parse_date(x['modified_date']))
        
        self.update_table_from_data()

    def filter_models(self):
        """根据搜索框内容过滤模型列表"""
        search_text = self.search_input.text().lower()
        
        # 从原始数据中过滤
        filtered_data = [
            model for model in self.original_models_data
            if search_text in model['name'].lower() or search_text in model['tag'].lower()
        ]
        
        # 应用当前排序
        self.models_data = filtered_data
        self.sort_models()

    def clear_search(self):
        """清除搜索框内容"""
        self.search_input.clear()
        self.filter_models() # 重新应用当前排序

    def update_table_from_data(self):
        """根据存储的模型数据更新表格"""
        self.model_table.setRowCount(0) # 清空现有行
        for model in self.models_data:
            self.add_model_to_table(model)

    def add_model_to_table(self, model):
        """将单个模型数据添加到表格中"""
        row_position = self.model_table.rowCount()
        self.model_table.insertRow(row_position)
        
        # 模型名称
        model_name_item = QTableWidgetItem(model['name'])
        model_name_item.setData(Qt.UserRole, model['full_name']) # 存储完整名称
        self.model_table.setItem(row_position, 0, model_name_item)
        
        # 模型标签
        tag_item = QTableWidgetItem(model['tag'])
        self.model_table.setItem(row_position, 1, tag_item)
        
        # 模型大小
        size_item = QTableWidgetItem(model['size'])
        self.model_table.setItem(row_position, 2, size_item)
        
        # 模型修改日期
        date_item = QTableWidgetItem(model['modified_date'])
        self.model_table.setItem(row_position, 3, date_item)

    def on_delete_finished(self, success, message):
        """删除完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, self.tr("Success"), message)
            self.status_label.setText(self.tr("Model deleted successfully"))
            # 重新加载模型列表
            self.load_models()
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Delete failed: %1").replace("%1", message))
            self.status_label.setText(self.tr("Model deletion failed"))

    def on_update_finished(self, success, message):
        """更新完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, self.tr("Success"), message)
            self.status_label.setText(self.tr("Model updated successfully"))
            self.load_models()
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Update failed: %1").replace("%1", message))
            self.status_label.setText(self.tr("Model update failed"))

    def show_context_menu(self, position):
        """显示右键菜单"""
        selected_items = self.model_table.selectedItems()
        if not selected_items:
            return

        menu = QMenu(self)

        # 获取选中行的模型完整名称
        row = selected_items[0].row()
        model_full_name = self.model_table.item(row, 0).data(Qt.UserRole)

        # 添加导出选项
        export_action = menu.addAction(self.tr("Export Selected Model"))
        export_action.triggered.connect(lambda: self.export_model_context_menu(model_full_name))

        # 添加导入选项
        import_action = menu.addAction(self.tr("Import Model"))
        import_action.triggered.connect(lambda: self.import_model_context_menu(model_full_name))

        # 添加删除选项
        delete_action = menu.addAction(self.tr("Delete Selected Model"))
        delete_action.triggered.connect(lambda: self.delete_model_context_menu(model_full_name))

        # 添加更新选项
        update_action = menu.addAction(self.tr("Update Selected Model"))
        update_action.triggered.connect(lambda: self.update_model_context_menu(model_full_name))

        menu.exec(self.model_table.mapToGlobal(position))

    def export_model_context_menu(self, model_full_name):
        """从右键菜单导出模型"""
        export_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Select Export Path"), f"{model_full_name}.gguf", self.tr("GGUF Files (*.gguf);;All Files (*)"))
        
        if not export_path:
            return
        
        # 如果已有线程在运行，先清理
        if self.worker_thread and self.worker_thread.isRunning():
            try:
                self.worker_thread.finished.disconnect()
            except:
                pass
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                self.worker_thread.terminate()
                self.worker_thread.wait(500)
        
        self.status_label.setText(self.tr("Exporting model %1...").replace("%1", model_full_name))
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("export", model_full_name, export_path)
        self.worker_thread.finished.connect(self.on_export_finished)
        self.worker_thread.start()

    def import_model_context_menu(self, model_full_name):
        """从右键菜单导入模型"""
        # 选择导入文件
        import_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Model File to Import"), "", self.tr("GGUF Files (*.gguf);;All Files (*)"))
        
        if not import_path:
            return
        
        # 获取文件名作为模型名
        model_name = Path(import_path).stem
        
        # 验证文件名是否包含特殊字符
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', model_name):
            # 如果文件名包含特殊字符，提示用户输入新的模型名
            new_model_name, ok = QInputDialog.getText(
                self, self.tr("Model Name"), 
                self.tr("The file name contains special characters. Please enter a valid model name:"), 
                text=model_name.replace(re.sub(r'[^a-zA-Z0-9_-]', '', model_name), ''))
            
            if not ok:
                self.status_label.setText(self.tr("Import operation cancelled"))
                return
            
            if not new_model_name:
                QMessageBox.warning(self, self.tr("Warning"), self.tr("Model name cannot be empty"))
                return
        else:
            # 询问是否需要修改模型名
            new_model_name, ok = QInputDialog.getText(
                self, self.tr("Model Name"), 
                self.tr("Please enter model name (optional):"), 
                text=model_name)
            
            # 如果用户取消输入对话框，返回
            if not ok:
                self.status_label.setText(self.tr("Import operation cancelled"))
                return
            
            # 如果用户没有输入新名称，使用默认名称
            if not new_model_name:
                new_model_name = model_name
        
        # 验证模型名是否有效
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_model_name):
            QMessageBox.warning(self, self.tr("Warning"), 
                              self.tr("Model name can only contain letters, numbers, underscores, and hyphens"))
            return
        
        # 如果已有线程在运行，先清理
        if self.worker_thread and self.worker_thread.isRunning():
            try:
                self.worker_thread.finished.disconnect()
            except:
                pass
            self.worker_thread.quit()
            if not self.worker_thread.wait(1000):
                self.worker_thread.terminate()
                self.worker_thread.wait(500)
        
        self.status_label.setText(self.tr("Importing model %1...").replace("%1", new_model_name))
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("import", import_path, new_model_name)
        self.worker_thread.finished.connect(self.on_import_finished)
        self.worker_thread.start()

    def delete_model_context_menu(self, model_full_name):
        """从右键菜单删除模型"""
        reply = QMessageBox.question(
            self, self.tr("Confirm Deletion"),
            self.tr("Are you sure you want to delete the model \"%1\"?").replace("%1", model_full_name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 如果已有线程在运行，先清理
            if self.worker_thread and self.worker_thread.isRunning():
                try:
                    self.worker_thread.finished.disconnect()
                except:
                    pass
                self.worker_thread.quit()
                if not self.worker_thread.wait(1000):
                    self.worker_thread.terminate()
                    self.worker_thread.wait(500)
            
            self.status_label.setText(self.tr("Deleting model %1...").replace("%1", model_full_name))
            self.progress_bar.setVisible(True)
            
            self.worker_thread = WorkerThread("delete", model_full_name)
            self.worker_thread.finished.connect(self.on_delete_finished)
            self.worker_thread.start()
        else:
            self.status_label.setText(self.tr("Model deletion cancelled"))

    def update_model_context_menu(self, model_full_name):
        """从右键菜单更新模型"""
        reply = QMessageBox.question(
            self, self.tr("Confirm Update"),
            self.tr("Are you sure you want to update the model \"%1\"? This may take a while.").replace("%1", model_full_name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 如果已有线程在运行，先清理
            if self.worker_thread and self.worker_thread.isRunning():
                try:
                    self.worker_thread.finished.disconnect()
                except:
                    pass
                self.worker_thread.quit()
                if not self.worker_thread.wait(1000):
                    self.worker_thread.terminate()
                    self.worker_thread.wait(500)
            
            self.status_label.setText(self.tr("Updating model %1...").replace("%1", model_full_name))
            self.progress_bar.setVisible(True)
            
            self.worker_thread = WorkerThread("update", model_full_name)
            self.worker_thread.finished.connect(self.on_update_finished)
            self.worker_thread.start()
        else:
            self.status_label.setText(self.tr("Model update cancelled"))

    def keyPressEvent(self, event):
        """处理键盘快捷键"""
        if event.key() == Qt.Key_F5:
            # F5 刷新列表
            self.load_models()
        elif event.key() == Qt.Key_Delete:
            # Delete 键删除选中的模型
            self.delete_model()
        elif event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            # Ctrl+F 聚焦到搜索框
            self.search_input.setFocus()
            self.search_input.selectAll()
        elif event.key() == Qt.Key_Escape:
            # Esc 键清除搜索
            self.search_input.clear()
        else:
            super().keyPressEvent(event)




def main():
    # Linux desktop environments use an app's .desktop file to integrate the app
    # in to their application menus. The .desktop file of this app will include
    # the StartupWMClass key, set to app's formal name. This helps associate the
    # app's windows to its menu item.
    #
    # For association to work, any windows of the app must have WMCLASS property
    # set to match the value set in app's desktop file. For PySide6, this is set
    # with setApplicationName().

    # Find the name of the module that was used to start the app
    app_module = sys.modules["__main__"].__package__
    
    # Set application name with fallback
    try:
        if app_module:
            # Retrieve the app's metadata
            metadata = importlib.metadata.metadata(app_module)
            QtWidgets.QApplication.setApplicationName(metadata["Formal-Name"])
        else:
            # Fallback when running script directly
            QtWidgets.QApplication.setApplicationName("OlaMoMa")
    except (ValueError, KeyError, importlib.metadata.PackageNotFoundError):
        # Fallback for any metadata-related errors
        QtWidgets.QApplication.setApplicationName("OlaMoMa")

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if app:
        try:
            # Ensure the application stays alive and processes events
            exit_code = app.exec()
            # Clean up threads before exiting
            if window and window.worker_thread and window.worker_thread.isRunning():
                try:
                    window.worker_thread.finished.disconnect()
                except:
                    pass
                window.worker_thread.quit()
                if not window.worker_thread.wait(2000):
                    window.worker_thread.terminate()
                    window.worker_thread.wait(1000)
            sys.exit(exit_code)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            if window and window.worker_thread and window.worker_thread.isRunning():
                window.worker_thread.cancel()
                window.worker_thread.quit()
                window.worker_thread.wait(2000)
            sys.exit(0)

    return app, window



if __name__ == "__main__":
    app, window = main()
    if app:
        try:
            # Ensure the application stays alive and processes events
            exit_code = app.exec()
            # Clean up threads before exiting
            if window and window.worker_thread and window.worker_thread.isRunning():
                try:
                    window.worker_thread.finished.disconnect()
                except:
                    pass
                window.worker_thread.quit()
                if not window.worker_thread.wait(2000):
                    window.worker_thread.terminate()
                    window.worker_thread.wait(1000)
            sys.exit(exit_code)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            if window and window.worker_thread and window.worker_thread.isRunning():
                window.worker_thread.cancel()
                window.workerThread.quit()
                window.worker_thread.wait(2000)
            sys.exit(0)
