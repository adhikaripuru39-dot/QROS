import re
with open(r'C:\Users\adhik\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config\terminal.ini', 'r', encoding='utf-16le') as f:
    lines = f.readlines()
    for line in lines:
        if 'bar' in line.lower() or 'max' in line.lower():
            print(line.strip())
