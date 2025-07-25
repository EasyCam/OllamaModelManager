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
                             QMessageBox, QProgressBar, QInputDialog)
from PySide6.QtCore import Qt, QThread, Signal

class OllamaManager:
    """管理Ollama模型的类"""
    
    def __init__(self):
        self.ollama_path = self.find_ollama()
    
    def find_ollama(self):
        """查找Ollama可执行文件"""
        # 常见的Ollama安装路径
        possible_paths = [
            "ollama",
            "C:\\Program Files\\Ollama\\ollama.exe",
            "C:\\Users\\{}\\AppData\\Local\\Ollama\\ollama.exe".format(os.getenv('USERNAME')),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果在常见路径中找不到，尝试在PATH中查找
        try:
            result = subprocess.run(["where", "ollama"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def list_models(self):
        """列出所有已下载的模型"""
        if not self.ollama_path:
            raise Exception("未找到Ollama可执行文件")
        
        try:
            result = subprocess.run([self.ollama_path, "list"], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                raise Exception(f"获取模型列表失败: {result.stderr}")
            
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
            raise Exception(f"列出模型时出错: {str(e)}")
    
    def export_model(self, model_name, export_path):
        """导出模型到指定路径"""
        if not self.ollama_path:
            raise Exception("未找到Ollama可执行文件")
        
        try:
            # 使用 ollama show --modelfile 命令获取模型文件内容
            cmd = [self.ollama_path, "show", "--modelfile", model_name]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                raise Exception(f"获取模型文件失败: {result.stderr}")
            
            # 解析 Modelfile 内容找到实际的模型文件路径
            modelfile_content = result.stdout
            model_file_path = None
            
            # 查找 FROM 行中的模型文件路径
            for line in modelfile_content.split('\n'):
                if line.startswith('FROM '):
                    model_file_path = line.split(' ')[1].strip()
                    break
            
            if not model_file_path:
                raise Exception("无法找到模型文件路径")
            
            # 如果模型文件路径是相对路径，则转换为绝对路径
            if model_file_path.startswith('~'):
                model_file_path = os.path.expanduser(model_file_path)
            elif not os.path.isabs(model_file_path):
                # 假设模型文件在 Ollama 默认存储路径下
                if os.name == 'nt':  # Windows系统
                    ollama_models_dir = os.environ.get('OLLAMA_MODELS', os.path.expanduser('~/.ollama/models'))
                else:  # Unix-like系统
                    ollama_models_dir = os.environ.get('OLLAMA_MODELS', os.path.expanduser('~/.ollama/models'))
                model_file_path = os.path.join(ollama_models_dir, 'blobs', model_file_path)
            # 如果模型文件路径已经是绝对路径，直接使用
            # 注意：在Windows系统中，路径可能包含反斜杠，需要确保正确处理
            
            # 检查模型文件是否存在
            if not os.path.exists(model_file_path):
                raise Exception(f"模型文件不存在: {model_file_path}")
            
            # 复制模型文件到导出路径
            import shutil
            shutil.copy2(model_file_path, export_path)
            
            return True
        except Exception as e:
            raise Exception(f"导出模型时出错: {str(e)}")
    
    def import_model(self, import_path, new_model_name=None):
        """从指定路径导入模型"""
        if not self.ollama_path:
            raise Exception("未找到Ollama可执行文件")
        
        try:
            # 使用ollama cp命令导入模型
            cmd = [self.ollama_path, "cp", import_path]
            if new_model_name:
                cmd.append(new_model_name)
                
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                raise Exception(f"导入模型失败: {result.stderr}")
                
            return True
        except Exception as e:
            raise Exception(f"导入模型时出错: {str(e)}")


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
                self.finished.emit(True, f"模型 {model_name} 已成功导出到 {export_path}")
            elif self.operation == "import":
                manager = OllamaManager()
                import_path = self.args[0]
                new_model_name = self.args[1] if len(self.args) > 1 else None
                manager.import_model(import_path, new_model_name)
                self.finished.emit(True, f"模型已成功从 {import_path} 导入")
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama 模型管理器")
        self.setGeometry(100, 100, 600, 400)
        
        self.manager = OllamaManager()
        self.worker_thread = None
        
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 标题
        title_label = QLabel("Ollama 模型管理器")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 模型列表
        layout.addWidget(QLabel("已下载的模型:"))
        self.model_list = QListWidget()
        layout.addWidget(self.model_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("刷新列表")
        self.refresh_button.clicked.connect(self.load_models)
        button_layout.addWidget(self.refresh_button)
        
        self.export_button = QPushButton("导出选中模型")
        self.export_button.clicked.connect(self.export_model)
        button_layout.addWidget(self.export_button)
        
        self.import_button = QPushButton("导入模型")
        self.import_button.clicked.connect(self.import_model)
        button_layout.addWidget(self.import_button)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def load_models(self):
        """加载模型列表"""
        self.status_label.setText("正在加载模型列表...")
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
            self.status_label.setText(f"已加载 {len(models)} 个模型")
        else:
            QMessageBox.critical(self, "错误", f"加载模型列表失败: {data}")
            self.status_label.setText("加载模型列表失败")
    
    def export_model(self):
        """导出选中的模型"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个模型")
            return
        
        model_name = selected_items[0].text()
        
        # 选择导出路径
        export_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出路径", f"{model_name}.gguf", "GGUF Files (*.gguf);;All Files (*)")
        
        if not export_path:
            return
        
        self.status_label.setText(f"正在导出模型 {model_name}...")
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("export", model_name, export_path)
        self.worker_thread.finished.connect(self.on_export_finished)
        self.worker_thread.start()
    
    def on_export_finished(self, success, message):
        """导出完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.status_label.setText("模型导出成功")
        else:
            QMessageBox.critical(self, "错误", f"导出失败: {message}")
            self.status_label.setText("模型导出失败")
    
    def import_model(self):
        """导入模型"""
        # 选择导入文件
        import_path, _ = QFileDialog.getOpenFileName(
            self, "选择要导入的模型文件", "", "GGUF Files (*.gguf);;All Files (*)")
        
        if not import_path:
            return
        
        # 获取文件名作为模型名
        model_name = Path(import_path).stem
        
        # 询问是否需要修改模型名
        new_model_name, ok = QInputDialog.getText(
            self, "模型名称", "请输入模型名称 (可选):", text=model_name)
        
        # 如果用户取消输入对话框，返回
        if not ok:
            self.status_label.setText("导入操作已取消")
            return
        
        # 如果用户没有输入新名称，使用默认名称
        if not new_model_name:
            new_model_name = model_name
        
        self.status_label.setText(f"正在导入模型 {new_model_name}...")
        self.progress_bar.setVisible(True)
        
        self.worker_thread = WorkerThread("import", import_path, new_model_name)
        self.worker_thread.finished.connect(self.on_import_finished)
        self.worker_thread.start()
    
    def on_import_finished(self, success, message):
        """导入完成的回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.status_label.setText("模型导入成功")
            # 重新加载模型列表
            self.load_models()
        else:
            QMessageBox.critical(self, "错误", f"导入失败: {message}")
            self.status_label.setText("模型导入失败")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()