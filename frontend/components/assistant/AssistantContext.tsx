'use client';

import { createContext, useContext, useEffect } from 'react';
import type { PageAssistantContext } from '@/lib/assistant-context';

const PageContext = createContext<{
  pageData: PageAssistantContext | null;
  setPageData: (value: PageAssistantContext | null) => void;
}>({ pageData: null, setPageData: () => undefined });

export function AssistantPageContextProvider({ children, pageData, setPageData }: Readonly<{ children: React.ReactNode; pageData: PageAssistantContext | null; setPageData: (value: PageAssistantContext | null) => void }>) {
  return <PageContext.Provider value={{ pageData, setPageData }}>{children}</PageContext.Provider>;
}

export function useAssistantPageContext(pageData: PageAssistantContext) {
  const { setPageData } = useContext(PageContext);
  useEffect(() => {
    setPageData(pageData);
    return () => setPageData(null);
  }, [pageData, setPageData]);
}

export function useCurrentAssistantPageContext() {
  return useContext(PageContext).pageData;
}
