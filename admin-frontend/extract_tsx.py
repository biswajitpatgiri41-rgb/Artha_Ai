import pathlib
import re

# Read the gen_page.py
p = pathlib.Path(r'c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/admin-frontend/gen_page.py')
t = p.read_text()
lines = t.splitlines()

# Extract content from lines.append() calls up to line 464 (before the write code)
tsx_lines = []
for i, line in enumerate(lines[:464]):
    # Match lines.append('...') or lines.append("...")
    m = re.match(r"^lines\.append\(['\"](.*)['\"]\)$", line)
    if m:
        tsx_lines.append(m.group(1))
    elif line.strip() == '':
        tsx_lines.append('')

# Remove leading empty line if present
if tsx_lines and tsx_lines[0] == '':
    tsx_lines = tsx_lines[1:]

# Add the missing closing brace for the function
tsx_lines.append('}')

print('Extracted lines:', len(tsx_lines))
tsx_content = '\n'.join(tsx_lines)
out = pathlib.Path(r'c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/admin-frontend/app/overview/page.tsx')
out.write_text(tsx_content, encoding='utf-8')
print('Written:', len(tsx_content), 'chars')
# Verify
print('First 5:')
for l in tsx_lines[:5]:
    print(f'  {repr(l)}')
print('Last 5:')
for l in tsx_lines[-5:]:
    print(f'  {repr(l)}')