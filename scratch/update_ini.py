import os

ini_path = r'C:\Users\adhik\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config\terminal.ini'

with open(ini_path, 'r', encoding='utf-16le') as f:
    content = f.read()

# Make sure [Charts] exists, otherwise append it
if '[Charts]' in content:
    # replace MaxBars if it exists
    if 'MaxBars=' in content:
        import re
        content = re.sub(r'MaxBars=\d+', 'MaxBars=10000000', content)
    else:
        content = content.replace('[Charts]', '[Charts]\nMaxBars=10000000')
else:
    content += '\n[Charts]\nMaxBars=10000000\n'

with open(ini_path, 'w', encoding='utf-16le') as f:
    f.write(content)

print("Updated terminal.ini with MaxBars=10000000")
