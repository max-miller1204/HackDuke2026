import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from 'recharts';

const MONO = "'JetBrains Mono', 'Fira Code', monospace";

const STAGES = {
  WAKE: { value: 5, color: '#60a5fa' },
  REM: { value: 4, color: '#f87171' },
  N1: { value: 3, color: '#5eead4' },
  N2: { value: 2, color: '#4ade80' },
  N3: { value: 1, color: '#a78bfa' },
};

type StageName = keyof typeof STAGES;

const data: { time: string; stage: StageName }[] = [
  { time: '22:00', stage: 'WAKE' },
  { time: '22:30', stage: 'N1' },
  { time: '23:00', stage: 'N2' },
  { time: '23:30', stage: 'N3' },
  { time: '00:00', stage: 'N3' },
  { time: '00:30', stage: 'N2' },
  { time: '01:00', stage: 'REM' },
  { time: '01:30', stage: 'N1' },
  { time: '02:00', stage: 'N2' },
  { time: '02:30', stage: 'N3' },
  { time: '03:00', stage: 'N2' },
  { time: '03:30', stage: 'REM' },
  { time: '04:00', stage: 'N1' },
  { time: '04:30', stage: 'WAKE' },
  { time: '05:00', stage: 'N2' },
  { time: '05:30', stage: 'REM' },
  { time: '06:00', stage: 'WAKE' },
];

const chartData = data.map(d => ({
  time: d.time,
  value: STAGES[d.stage].value,
  stage: d.stage,
  color: STAGES[d.stage].color,
}));

const stageLabels: Record<number, string> = { 1: 'N3', 2: 'N2', 3: 'N1', 4: 'REM', 5: 'Wake' };

const HypnogramChart = () => (
  <div className="flex gap-4 items-stretch">
    <div className="flex-1 min-w-0">
      {/* N1 label */}
      <div className="mb-2">
        <span
          className="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded"
          style={{
            background: 'hsla(var(--primary), 0.1)',
            color: 'hsl(var(--primary))',
            fontFamily: MONO,
          }}
        >
          Your Light Sleep 12%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={chartData} barCategoryGap={1}>
          <XAxis
            dataKey="time"
            tick={{ fill: 'hsl(220, 12%, 48%)', fontSize: 9, fontFamily: MONO }}
            axisLine={{ stroke: 'hsl(230, 16%, 18%)' }}
            tickLine={false}
            interval={3}
          />
          <YAxis
            domain={[0, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tickFormatter={(v: number) => stageLabels[v] || ''}
            tick={{ fill: 'hsl(220, 12%, 48%)', fontSize: 9, fontFamily: MONO }}
            axisLine={false}
            tickLine={false}
            width={32}
          />
          <Tooltip
            contentStyle={{
              background: 'hsl(228, 24%, 10%)',
              border: '1px solid hsl(230, 16%, 18%)',
              borderRadius: 6,
              fontFamily: MONO,
              fontSize: 11,
              color: 'hsl(174, 72%, 52%)',
            }}
            itemStyle={{ color: 'hsl(174, 72%, 52%)' }}
            labelStyle={{ color: 'hsl(200, 20%, 85%)' }}
            formatter={(value: number, _name: string, props: { payload: { stage: string } }) => [props.payload.stage, 'Stage']}
            labelFormatter={(label: string) => `Time: ${label}`}
          />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>

    {/* Side stats */}
    <div
      className="flex flex-col justify-center gap-4 pl-4 border-l"
      style={{ borderColor: 'hsl(var(--border))' }}
    >
      <div>
        <div className="text-muted-foreground text-[10px] uppercase tracking-widest" style={{ fontFamily: MONO }}>Sleep</div>
        <div className="text-foreground text-xl font-bold" style={{ fontFamily: MONO }}>6h 15m</div>
      </div>
      <div>
        <div className="text-muted-foreground text-[10px] uppercase tracking-widest" style={{ fontFamily: MONO }}>Efficiency</div>
        <div className="text-xl font-bold" style={{ fontFamily: MONO, color: 'hsl(var(--primary))' }}>89%</div>
      </div>
      <div>
        <div className="text-muted-foreground text-[10px] uppercase tracking-widest" style={{ fontFamily: MONO }}>Frag. Index</div>
        <div className="text-xl font-bold" style={{ fontFamily: MONO, color: '#f87171' }}>18 <span className="text-xs font-normal">ev/hr</span></div>
      </div>
    </div>
  </div>
);

export default HypnogramChart;
