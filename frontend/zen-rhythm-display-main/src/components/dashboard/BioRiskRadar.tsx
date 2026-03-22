import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';
import { Info } from 'lucide-react';
import { useState } from 'react';

const MONO = "'JetBrains Mono', 'Fira Code', monospace";

const data = [
  { subject: "Parkinson's", value: 18 },
  { subject: 'Dementia', value: 15 },
  { subject: 'Cog. Decline', value: 22 },
  { subject: 'Heart Failure', value: 12 },
  { subject: 'Mortality', value: 8 },
];

const BioRiskRadar = () => {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-foreground text-sm font-semibold" style={{ fontFamily: MONO }}>
          Long-term Bio-Risk Matrix
        </h3>
        <button
          className="text-muted-foreground hover:text-primary transition-colors"
          onMouseEnter={() => setShowInfo(true)}
          onMouseLeave={() => setShowInfo(false)}
        >
          <Info size={14} />
        </button>
      </div>

      {showInfo && (
        <div
          className="absolute top-8 right-0 z-20 p-2 rounded text-[10px] max-w-48"
          style={{
            background: 'hsl(var(--popover))',
            border: '1px solid hsl(var(--border))',
            color: 'hsl(var(--muted-foreground))',
            fontFamily: MONO,
          }}
        >
          Research-based estimates – not a medical diagnosis.
        </div>
      )}

      <ResponsiveContainer width="100%" height={200}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="hsl(230, 16%, 18%)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: 'hsl(220, 12%, 48%)', fontSize: 9, fontFamily: MONO }}
          />
          <Radar
            dataKey="value"
            stroke="#f87171"
            fill="#f87171"
            fillOpacity={0.15}
            strokeWidth={2}
            style={{ filter: 'drop-shadow(0 0 6px rgba(248,113,113,0.5))' }}
          />
        </RadarChart>
      </ResponsiveContainer>

      <p className="text-[9px] text-muted-foreground mt-1" style={{ fontFamily: MONO }}>
        Cortical/metabolic N1 fragmentation and REM density metrics.
      </p>
    </div>
  );
};

export default BioRiskRadar;
