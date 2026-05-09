# UTF-8 编码测试
import sys
import os
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"stdout encoding: {sys.stdout.encoding}")
print(f"stderr encoding: {sys.stderr.encoding}")
print(f"PYTHONUTF8: {os.environ.get('PYTHONUTF8', 'not set')}")
print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'not set')}")
print("中文测试: 肖申克的救赎")
