import pathlib

p = pathlib.Path(r'c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/admin-frontend/lib/auth.tsx')
content = p.read_text(encoding='utf-8')

content += (
    "\n"
    "export function useAdminAuth() {\n"
    "  const context = useContext(AuthContext);\n"
    "  if (!context) {\n"
    "    throw new Error('useAdminAuth must be used within AdminAuthProvider');\n"
    "  }\n"
    "  return context;\n"
    "}\n\n"
    "export function useAdminRole(requiredRole: AdminRole) {\n"
    "  const { user, isAuthenticated } = useAdminAuth();\n"
    "  \n"
    "  if (!isAuthenticated || !user) return false;\n"
    "  return hasPermission(user.role, requiredRole);\n"
    "}\n\n"
    "export function AdminOnly({ children, requiredRole = 'ADMIN' }: { \n"
    "  children: ReactNode; \n"
    "  requiredRole?: AdminRole; \n"
    "}) {\n"
    "  const { user, isAuthenticated, isLoading } = useAdminAuth();\n\n"
    "  if (isLoading) {\n"
    "    return (\n"
    "      <div className=\"flex items-center justify-center h-64\">\n"
    "        <Loader2 className=\"w-8 h-8 text-admin-neon-green animate-spin\" />\n"
    "      </div>\n"
    "    );\n"
    "  }\n\n"
    "  if (!isAuthenticated || !user || !hasPermission(user.role, requiredRole)) {\n"
    "    return (\n"
    "      <div className=\"admin-card p-8 text-center\">\n"
    "        <AlertTriangle className=\"w-12 h-12 text-admin-amber mx-auto mb-4\" />\n"
    "        <h3 className=\"text-admin-text-primary text-lg font-medium mb-2\">\n"
    "          Access Denied\n"
    "        </h3>\n"
    "        <p className=\"text-admin-text-secondary\">\n"
    "          This section requires {requiredRole} role or higher.\n"
    "        </p>\n"
    "      </div>\n"
    "    );\n"
    "  }\n\n"
    "  return <>{children}</>;\n"
    "}\n"
)

p.write_text(content, encoding='utf-8')
print('Part 3 done')