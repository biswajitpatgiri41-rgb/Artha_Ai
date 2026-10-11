import pathlib

p = pathlib.Path(r'c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/admin-frontend/app/(admin)/overview/page.tsx')
p.parent.mkdir(parents=True, exist_ok=True)
print('Directory created')