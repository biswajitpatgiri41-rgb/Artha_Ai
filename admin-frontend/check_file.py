import pathlib

p = pathlib.Path(r'c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/admin-frontend/app/(admin)/overview/page.tsx')
content = p.read_text(encoding='utf-8')
print(len(content))