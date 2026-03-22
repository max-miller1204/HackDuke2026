import { useEffect, useRef, useState } from 'react';

const MONO = "'JetBrains Mono', 'Fira Code', monospace";

const LOGS = [
  '[03:14:22] INTERFERENCE DETECTED: UNIDENTIFIED 432Hz FREQUENCY OVERLAP',
  '[03:14:25] INITIATING NEURAL RE-SYNC PROTOCOL T-DELTA',
  '[04:02:11] PHASE-LOCKED STABILIZED. N1 DURATION REDUCED BY 4.2%',
  '[06:30:03] ANALYSIS COMPLETE. UPLOADING TO GUARDIAN_CORE...',
];

const SystemLog = () => {
  const [visibleLogs, setVisibleLogs] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < LOGS.length) {
        setVisibleLogs(prev => [...prev, LOGS[i]]);
        i++;
      } else {
        clearInterval(interval);
      }
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [visibleLogs]);

  return (
    <div
      className="rounded-lg p-4"
      style={{
        background: 'hsl(var(--card))',
        border: '1px solid hsl(var(--border))',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <span
          className="text-[10px] uppercase tracking-widest text-muted-foreground"
          style={{ fontFamily: MONO }}
        >
          DIAGNOSTICS_SYSTEM.LOG
        </span>
      </div>
      <div
        ref={scrollRef}
        className="max-h-24 overflow-y-auto space-y-1"
        style={{ scrollbarWidth: 'thin', scrollbarColor: 'hsl(var(--border)) transparent' }}
      >
        {visibleLogs.map((log, i) => (
          <p
            key={i}
            className="text-[10px] text-muted-foreground leading-relaxed"
            style={{ fontFamily: MONO }}
          >
            {log}
          </p>
        ))}
      </div>
    </div>
  );
};

export default SystemLog;
