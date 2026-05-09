# UTF-8 编码启动脚本
# 使用方法: .\run.ps1 <脚本名> <参数>
# 例如: .\run.ps1 import_to_db.py --work-id 0101000001

$env:PYTHONUTF8 = '1'
python $args
