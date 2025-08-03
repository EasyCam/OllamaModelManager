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
                             QMessageBox, QProgressBar, QInputDialog, QMenuBar, QMenu)
from PySide6.QtCore import Qt, QThread, Signal, QTranslator, QLocale
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
            "C:\\Users\\{}\\AppData\\Local\\Ollama\\ollama.exe".format(os.getenv('USERNAME')),
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果在常见路径中找不到，尝试在PATH中查找
        try:
            # 在Linux系统上使用 'which' 命令
            if os.name == 'posix':
                result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
            else:
                result = subprocess.run(["where", "ollama"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def list_models(self):
        """列出所有已下载的模型"""
        if not self.ollama_path:
            raise Exception(self.tr("Ollama executable not found"))
        
        try:
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=True, encoding='utf-8', errors='ignore')
            if result.returncode != 0:
                raise Exception(self.tr_with_args("Failed to get model list: %1", result.stderr))
            
            models = []
            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
            
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        models.append(model_name)
            
            return models
        except Exception as e:
            raise Exception(self.tr_with_args("Error listing models: %1", str(e)))
    
    def export_model(self, model_name, export_path):
        """导出模型到指定路径"""
        if not self.ollama_path:
            raise Exception(self.tr("Ollama executable not found"))
        
        try:
            # 使用 ollama show --modelfile 命令获取模型文件内容
            cmd = [self.ollama_path, "show", "--modelfile", model_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='ignore')
            
            if result.returncode != 0:
                raise Exception(self.tr_with_args("Failed to get model file: %1", result.stderr))
            
            # 解析 Modelfile 内容找到实际的模型文件路径
            modelfile_content = result.stdout
            model_file_path = None
            
            # 查找 FROM 行中的模型文件路径
            for line in modelfile_content.split('\n'):
                if line.startswith('FROM '):
                    model_file_path = line.split(' ')[1].strip()
                    break
            
            if not model_file_path:
                raise Exception(self.tr("Could not find model file path"))
            
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
                raise Exception(self.tr_with_args("Model file does not exist: %1", model_file_path))
            
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
            raise Exception(self.tr_with_args("Error exporting model: %1", str(e)))
    
    def import_model(self, import_path, new_model_name=None):
        """从指定路径导入模型"""
        if not self.ollama_path:
            raise Exception(self.tr("Ollama executable not found"))
        
        # 检查Ollama服务是否运行
        try:
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=True, encoding='utf-8', errors='ignore', timeout=10)
            if result.returncode != 0:
                raise Exception(self.tr("Ollama service is not running. Please start Ollama first."))
        except subprocess.TimeoutExpired:
            raise Exception(self.tr("Ollama service is not responding. Please start Ollama first."))
        except Exception as e:
            raise Exception(self.tr_with_args("Failed to connect to Ollama service: %1", str(e)))
        
        try:
            # 检查文件是否存在
            if not os.path.exists(import_path):
                raise Exception(self.tr_with_args("File does not exist: %1", import_path))
            
            # 检查文件是否为GGUF格式
            if not import_path.lower().endswith('.gguf'):
                raise Exception(self.tr("File must be in GGUF format"))
            
            # 获取文件的绝对路径
            import_path = os.path.abspath(import_path)
            
            # 如果没有指定模型名，使用文件名（去掉扩展名）
            if not new_model_name:
                new_model_name = os.path.splitext(os.path.basename(import_path))[0]
            
            # 验证模型名是否有效（不能包含特殊字符）
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', new_model_name):
                raise Exception(self.tr("Model name can only contain letters, numbers, underscores, and hyphens"))
            
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
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8', errors='ignore')
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                    raise Exception(self.tr_with_args("Failed to import model: %1", error_msg))
                
                return True
            finally:
                # 清理临时文件
                if os.path.exists(temp_modelfile):
                    try:
                        os.remove(temp_modelfile)
                    except:
                        pass
                        
        except Exception as e:
            raise Exception(self.tr_with_args("Error importing model: %1", str(e)))
    
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
TEMPLATE "{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"

# 停止标记
STOP "<|im_start|>"
STOP "<|im_end|>"
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
TEMPLATE "{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"

# 停止标记
STOP "<|im_start|>"
STOP "<|im_end|>"
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
TEMPLATE "{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"

# 停止标记
STOP "<|im_start|>"
STOP "<|im_end|>"
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
TEMPLATE "{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"

# 停止标记
STOP "<|im_start|>"
STOP "<|im_end|>"
"""


class WorkerThread(QThread):
    """工作线程，用于执行耗时操作"""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args
    
    def run(self):
        try:
            if self.operation == "list":
                manager = OllamaManager()
                models = manager.list_models()
                self.finished.emit(True, json.dumps(models))
            elif self.operation == "export":
                manager = OllamaManager()
                model_name, export_path = self.args
                manager.export_model(model_name, export_path)
                modelfile_path = os.path.splitext(export_path)[0] + ".modelfile"
                message = manager.tr_with_args("Model %1 successfully exported to %2 and Modelfile to %3", model_name, export_path, modelfile_path)
                self.finished.emit(True, message)
            elif self.operation == "import":
                manager = OllamaManager()
                import_path = self.args[0]
                new_model_name = self.args[1] if len(self.args) > 1 else None
                manager.import_model(import_path, new_model_name)
                
                # 检查是否使用了现有的Modelfile
                modelfile_path = os.path.splitext(import_path)[0] + ".modelfile"
                if os.path.exists(modelfile_path):
                    message = manager.tr_with_args("Model successfully imported from %1 using existing Modelfile", import_path)
                else:
                    message = manager.tr_with_args("Model successfully imported from %1 using default configuration", import_path)
                
                self.finished.emit(True, message)
        except Exception as e:
            self.finished.emit(False, str(e))


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
            # 假设翻译文件在当前目录的translations文件夹中
            self.translator.load("translations/omm_zh.qm")
        else:
            # 加载英文翻译
            # 假设翻译文件在当前目录的translations文件夹中
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
        self.load_models()
    
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
        
        # 模型列表
        layout.addWidget(QLabel(self.tr("Downloaded Models:")))
        self.model_list = QListWidget()
        layout.addWidget(self.model_list)
        
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
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel(self.tr("Ready"))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def load_models(self):
        """加载模型列表"""
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
            self.model_list.clear()
            for model in models:
                self.model_list.addItem(model)
            self.status_label.setText(self.tr("Loaded %n models", "", len(models)))
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to load model list: %1").replace("%1", data))
            self.status_label.setText(self.tr("Failed to load model list"))
    
    def export_model(self):
        """导出选中的模型"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a model first"))
            return
        
        model_name = selected_items[0].text()
        
        # 选择导出路径
        export_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Select Export Path"), f"{model_name}.gguf", self.tr("GGUF Files (*.gguf);;All Files (*)"))
        
        if not export_path:
            return
        
        self.status_label.setText(self.tr("Exporting model %1...").replace("%1", model_name))
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("export", model_name, export_path)
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


def main():
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="Language code (e.g., 'zh' for Chinese, 'en' for English)")
    args, unknown = parser.parse_known_args()
    language_code = args.lang
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = MainWindow(language_code)
    window.show()
    return app, window

if __name__ == "__main__":
    app, window = main()
    if app:
        sys.exit(app.exec())

