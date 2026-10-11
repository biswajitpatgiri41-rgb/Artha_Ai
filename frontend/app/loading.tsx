import { StatusState } from '@/components/ui';

export default function Loading() {
  return <main className="mx-auto flex min-h-[60vh] max-w-7xl items-center px-6"><div className="w-full"><StatusState kind="loading" title="Loading research workspace" message="Preparing the mock dashboard surface..." /></div></main>;
}
