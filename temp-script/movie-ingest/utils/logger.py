# -*- coding: utf-8 -*-
"""
日志工具 - Windows UTF-8 兼容
"""
import os
import sys

# Windows UTF-8 兼容：必须在其他 import 之前设置
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

from datetime import datetime


class Logger:
    """简单日志类"""
    
    @staticmethod
    def info(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [INFO] {message}", flush=True)
        
    @staticmethod
    def error(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [ERROR] {message}", file=sys.stderr, flush=True)
        
    @staticmethod
    def warning(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [WARN] {message}", flush=True)
        
    @staticmethod
    def success(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [OK] {message}", flush=True)
