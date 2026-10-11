import pathlib

content = '''\"use client\";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Minus,
  Loader2,
  Cpu,
  Database,
  Database as DatabaseIcon,
  HardDrive,
  Network,
  Zap,
  Activity,
  Brain,
  FlaskConical,
  Shield,
  Layers,
  TrendingUp,
  Bell,
  Terminal,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { redirect } from "next/navigation";'''
pathlib.Path('c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/admin-frontend/app/overview/page.tsx').write_text(content, encoding='utf-8')
print('Part 1 written')