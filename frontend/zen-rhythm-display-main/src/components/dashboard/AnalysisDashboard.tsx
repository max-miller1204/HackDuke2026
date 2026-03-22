import { useNavigate } from 'react-router-dom';
import VulnerabilityGauge from './VulnerabilityGauge';
import HypnogramChart from './HypnogramChart';
import BioRiskRadar from './BioRiskRadar';
import NeuralDesyncPlots from './NeuralDesyncPlots';
import SystemLog from './SystemLog';

const MONO = "'JetBrains Mono', 'Fira Code', monospace";

const AnalysisDashboard = () => {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen w-full"
      style={{ background: 'hsl(var(--background))' }}>
      
      {/* Navbar */}
      <nav className="flex items-center px-6 py-4">
        <span
          onClick={() => navigate('/')}
          className="cursor-pointer"
          style={{
            fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
            fontSize: '0.95rem',
            fontWeight: 700,
            color: 'rgba(255,255,255,0.85)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase' as const
          }}>
          SleepFM Clinical
        </span>
      </nav>
      <div className="max-w-5xl mx-auto px-6 py-12 md:px-12">
        {/* Header */}
        <h1
          className="font-bold text-foreground mb-2 text-center md:text-5xl lg:text-5xl text-3xl"
          style={{ fontFamily: "'Inter', sans-serif", lineHeight: 1.1 }}>
          
          Neural Storm Analysis:{' '}
          <span style={{ color: 'hsl(var(--primary))' }}>Light-Sleep Vulnerability Report</span>
        </h1>
        <p
          className="text-muted-foreground md:text-sm max-w-2xl mb-10 leading-relaxed pt-0 mt-[20px] text-center text-base mx-auto"
          style={{ fontFamily: MONO }}>
          
          Comprehensive mapping of cortical interference patterns and N1 stage architecture.
          High-frequency micro-arousals detected during REM transitions suggest external wave desynchronization.
        </p>

        {/* Row 1: Gauge + Bio-Risk */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Gauge card */}
          <div
            className="rounded-xl p-6 flex flex-col md:flex-row items-center gap-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_28px_hsla(var(--primary),0.18)] bg-[#161b22]"
            style={{
              background: 'hsla(var(--card), 0.5)',
              border: '1px solid hsl(var(--border))',
              boxShadow: '0 0 24px hsla(var(--primary), 0.06)',
              backdropFilter: 'blur(12px)'
            }}>
            
            <VulnerabilityGauge />
            <p
              className="text-xs text-muted-foreground leading-relaxed"
              style={{ fontFamily: MONO }}>
              
              {'>'} Detected 43 micro-arousals/transitions during the 02:00–04:00 window. Cortex response time is elevated. Recommend Phase-Locked acoustic shielding.
            </p>
          </div>

          {/* Bio-Risk */}
          <div
            className="rounded-xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_28px_hsla(var(--primary),0.18)] bg-[#161b22]"
            style={{
              background: 'hsla(var(--card), 0.5)',
              border: '1px solid hsl(var(--border))',
              boxShadow: '0 0 24px hsla(var(--primary), 0.06)',
              backdropFilter: 'blur(12px)'
            }}>
            
            <BioRiskRadar />
          </div>
        </div>

        {/* Row 2: Hypnogram + Neural Desync */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Hypnogram */}
          <div
            className="rounded-xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_28px_hsla(var(--primary),0.18)] bg-[#161b22]"
            style={{
              background: 'hsla(var(--card), 0.5)',
              border: '1px solid hsl(var(--border))',
              boxShadow: '0 0 24px hsla(var(--primary), 0.06)',
              backdropFilter: 'blur(12px)'
            }}>
            
            <h3 className="text-foreground text-sm font-semibold mb-3 flex items-center gap-2" style={{ fontFamily: MONO }}>
              <span style={{ color: 'hsl(var(--primary))' }}>✦</span> Sleep Architecture Hypnogram
            </h3>
            <HypnogramChart />
          </div>

          {/* Neural Desync */}
          <div
            className="rounded-xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_28px_hsla(var(--primary),0.18)] bg-[#161b22]"
            style={{
              background: 'hsla(var(--card), 0.5)',
              border: '1px solid hsl(var(--border))',
              boxShadow: '0 0 24px hsla(var(--primary), 0.06)',
              backdropFilter: 'blur(12px)'
            }}>
            
            <NeuralDesyncPlots />
          </div>
        </div>

        {/* System Log */}
        <div className="mb-6">
          <SystemLog />
        </div>

        {/* CTA */}
        <button
          onClick={() => navigate('/game')}
          className="w-full py-4 rounded-xl text-sm font-bold uppercase tracking-widest transition-all duration-200 active:scale-[0.98]"
          style={{
            background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(168, 80%, 44%))',
            color: 'hsl(var(--primary-foreground))',
            fontFamily: "'Inter', sans-serif",
            letterSpacing: '0.15em',
            boxShadow: '0 0 32px hsla(var(--primary), 0.3)'
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLElement).style.boxShadow = '0 0 48px hsla(174, 72%, 52%, 0.5)';
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLElement).style.boxShadow = '0 0 32px hsla(174, 72%, 52%, 0.3)';
          }}>
          
          Play to Clear the Fog
        </button>
      </div>
    </div>);

};

export default AnalysisDashboard;