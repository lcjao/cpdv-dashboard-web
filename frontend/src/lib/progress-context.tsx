import { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react';
import { ProgressSubscriber, type ProgressEvent } from './ws-client';

/** Global progress state for all long-running tasks */
export interface TaskProgress {
  id: string;           // unique key: `${tag}-${stage}`
  tag: string;          // 'train' | 'cpdv' | 'random' | ...
  stage: string;        // current stage name
  message: string;      // human-readable message
  percent?: number;     // 0-100
  timestamp: number;    // when received
  meta?: Record<string, unknown>; // extra fields (bridge, model, etc.)
}

/** Context value */
interface ProgressContextValue {
  tasks: TaskProgress[];
  /** Subscribe to a new tag (idempotent) */
  subscribe: (tag: string) => void;
  /** Unsubscribe from a tag */
  unsubscribe: (tag: string) => void;
  /** Clear completed/errored tasks */
  clearDone: () => void;
  /** Get latest progress for a specific tag */
  getLatest: (tag: string) => TaskProgress | undefined;
}

const ProgressContext = createContext<ProgressContextValue | null>(null);

/** Provider: manages single WS connection per tag set, feeds global task list */
export function ProgressProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<TaskProgress[]>([]);
  const subscribersRef = useRef<Map<string, ProgressSubscriber>>(new Map());
  const subscribedTagsRef = useRef<Set<string>>(new Set());

  const upsertTask = (evt: ProgressEvent) => {
    const id = `${evt.tag}-${evt.stage}`;
    const task: TaskProgress = {
      id,
      tag: evt.tag,
      stage: evt.stage,
      message: evt.message,
      percent: evt.percent,
      timestamp: Date.now(),
      meta: evt,
    };
    setTasks(prev => {
      const idx = prev.findIndex(t => t.id === id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = task;
        return next;
      }
      return [...prev, task];
    });
    // Auto-clear old completed tasks after 10s
    if (evt.stage === 'done' || evt.stage === 'error') {
      setTimeout(() => {
        setTasks(prev => prev.filter(t => t.id !== id));
      }, 10000);
    }
  };

  const subscribe = (tag: string) => {
    if (subscribedTagsRef.current.has(tag)) return;
    subscribedTagsRef.current.add(tag);
    const sub = new ProgressSubscriber([...subscribedTagsRef.current], upsertTask);
    subscribersRef.current.set(tag, sub);
    sub.connect();
  };

  const unsubscribe = (tag: string) => {
    if (!subscribedTagsRef.current.has(tag)) return;
    subscribedTagsRef.current.delete(tag);
    const sub = subscribersRef.current.get(tag);
    if (sub) {
      sub.disconnect();
      subscribersRef.current.delete(tag);
    }
    // Reconnect remaining tags if any
    if (subscribedTagsRef.current.size > 0) {
      const newSub = new ProgressSubscriber([...subscribedTagsRef.current], upsertTask);
      subscribersRef.current.clear();
      [...subscribedTagsRef.current].forEach(t => subscribersRef.current.set(t, newSub));
      newSub.connect();
    }
  };

  const clearDone = () => {
    setTasks(prev => prev.filter(t => t.stage !== 'done' && t.stage !== 'error'));
  };

  const getLatest = (tag: string) => {
    return [...tasks].reverse().find(t => t.tag === tag);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      subscribersRef.current.forEach(s => s.disconnect());
      subscribersRef.current.clear();
      subscribedTagsRef.current.clear();
    };
  }, []);

  return (
    <ProgressContext.Provider value={{ tasks, subscribe, unsubscribe, clearDone, getLatest }}>
      {children}
    </ProgressContext.Provider>
  );
}

/** Hook to access global progress */
export function useProgress() {
  const ctx = useContext(ProgressContext);
  if (!ctx) throw new Error('useProgress must be used within ProgressProvider');
  return ctx;
}

/** Hook for a specific tag's latest progress */
export function useTagProgress(tag: string) {
  const { subscribe, unsubscribe, getLatest } = useProgress();
  useEffect(() => {
    subscribe(tag);
    return () => unsubscribe(tag);
  }, [tag, subscribe, unsubscribe]);
  return getLatest(tag);
}

/** Hook for all active (non-done) tasks */
export function useActiveTasks() {
  const { tasks } = useProgress();
  return tasks.filter(t => t.stage !== 'done' && t.stage !== 'error');
}