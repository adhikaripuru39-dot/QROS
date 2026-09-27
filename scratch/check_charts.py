import re

ini_path = r'C:\Users\adhik\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config\terminal.ini'

with open(ini_path, 'r', encoding='utf-16le') as f:
    lines = f.readlines()

in_charts = False
for line in lines:
    if line.strip().startswith('['):
        in_charts = (line.strip() == '[Charts]')
    if in_charts:
        print(line.strip())
