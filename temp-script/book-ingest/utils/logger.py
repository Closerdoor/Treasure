# -*- coding: utf-8 -*-
"""
日志工具
"""
import sys
from datetime import datetime

class Logger:
    """日志输出"""
    
    COLORS = {
        'reset': '\033[0m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
    }
    
    @staticmethod
    def _get_timestamp():
        return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def _print(color, prefix, message):
        timestamp = Logger._get_timestamp()
        if sys.platform == 'win32':
            print(f"[{timestamp}] {prefix} {message}")
        else:
            color_code = Logger.COLORS.get(color, '')
            reset = Logger.COLORS['reset']
            print(f"{color_code}[{timestamp}] {prefix}{reset} {message}")
    
    @staticmethod
    def info(message):
        Logger._print('blue', '[INFO]', message)
    
    @staticmethod
    def success(message):
        Logger._print('green', '[OK]', message)
    
    @staticmethod
    def warning(message):
        Logger._print('yellow', '[WARN]', message)
    
    @staticmethod
    def error(message):
        Logger._print('red', '[ERR]', message)
    
    @staticmethod
    def debug(message):
        Logger._print('cyan', '[...]', message)
