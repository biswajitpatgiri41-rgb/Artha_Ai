'use client';

import { StatusState } from '@/components/ui';

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="mx-auto flex min-h-[60vh] max-w-7xl items-center px-6"><div className="w-full"><StatusState kind="error" title="Research workspace unavailable" message="The page encountered an unexpected frontend error." actionLabel="Try again" onAction={reset} /></div></main>;
}
