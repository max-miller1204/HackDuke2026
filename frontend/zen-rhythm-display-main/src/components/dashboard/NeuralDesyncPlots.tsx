import { LineChart, Line, ResponsiveContainer, XAxis, ReferenceDot } from 'recharts';

const MONO = "'JetBrains Mono', 'Fira Code', monospace";

// Generate wave data
const generateWave = (freq: number, amp: number, offset: number, points: number) =>
  Array.from({ length: points }, (_, i) => ({
    x: i,
    y: Math.sin((i / points) * Math.PI * 2 * freq + offset) * amp,
  }));

const alphaData = generateWave(3, 1, 0, 60).map((p, i) => ({
  ...p,
  hr: Math.sin((i / 60) * Math.PI * 2 * 2 + 1.5) * 0.7 + (i > 35 && i < 45 ? 0.8 : 0),
}));

const breathData = generateWave(2, 1, 0.5, 60).map((p, i) => ({
  ...p,
  o2: Math.sin((i / 60) * Math.PI * 2 * 4 + 2) * 0.4 - (i > 40 && i < 50 ? 0.5 : 0),
}));

const PlotCard = ({
  title, subtitle, data, keys, colors, annotation,
}: {
  title: string;
  subtitle: string;
  data: Record<string, number>[];
  keys: [string, string];
  colors: [string, string];
  annotation?: { x: number; label: string };
}) => (
  <div>
    <div className="flex items-center gap-3 mb-2">
      {keys.map((k, i) => (
        <span key={k} className="text-[9px] uppercase tracking-widest" style={{ color: colors[i], fontFamily: MONO }}>
          {k === 'y' ? 'EEG_WAVE_ALPHA' : k === 'hr' ? 'HEART_RATE' : k === 'o2' ? 'OXYGEN_SATS' : 'BIO_SLEEP_RATE'}
        </span>
      ))}
      {annotation && (
        <span className="text-[9px] ml-auto" style={{ color: '#f87171', fontFamily: MONO }}>
          EVENT_DETECTED ↑
        </span>
      )}
    </div>
    <ResponsiveContainer width="100%" height={80}>
      <LineChart data={data}>
        <XAxis hide />
        <Line type="monotone" dataKey={keys[0]} stroke={colors[0]} dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey={keys[1]} stroke={colors[1]} dot={false} strokeWidth={1.2} strokeDasharray="4 2" />
        {annotation && (
          <ReferenceDot x={annotation.x} y={0} r={0} label="" />
        )}
      </LineChart>
    </ResponsiveContainer>
    <p className="text-[9px] text-muted-foreground mt-1" style={{ fontFamily: MONO }}>
      {subtitle}
    </p>
  </div>
);

const NeuralDesyncPlots = () => (
  <div className="space-y-5">
    <h3 className="text-foreground text-sm font-semibold" style={{ fontFamily: MONO }}>
      Neural Desynchronization
    </h3>
    <PlotCard
      title="EEG Alpha vs Heart Rate"
      subtitle=">> Desynchronization moment at 03:14:22"
      data={alphaData}
      keys={['y', 'hr']}
      colors={['hsl(var(--primary))', '#f87171']}
      annotation={{ x: 40, label: 'Desync' }}
    />
    <PlotCard
      title="Breathing vs O2"
      subtitle="Breathing effort vs. Oxygen dips"
      data={breathData}
      keys={['y', 'o2']}
      colors={['hsl(var(--primary))', '#a78bfa']}
    />
  </div>
);

export default NeuralDesyncPlots;
