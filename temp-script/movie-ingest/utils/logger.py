# -*- coding: utf-8 -*-
"""
日志工具
"""
import sys
from datetime import datetime


class Logger:
    """简单日志类"""
    
    @staticmethod
    def info(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [INFO] {message}")
        
    @staticmethod
    def error(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [ERROR] {message}", file=sys.stderr)
        
    @staticmethod
    def warning(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [WARN] {message}")
        
    @staticmethod
    def success(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [OK] {message}")
