import { useState, useEffect } from 'react';

const STATUS_PHRASES = [
  '> SCANNING SLEEP EEG CHANNELS...',
  '> MAPPING N1 STAGE MICRO-AROUSALS...',
  '> DETECTING CORTICAL DESYNCHRONIZATION...',
  '> MEASURING REM TRANSITION LATENCY...',
  '> COMPUTING NEURAL STORM VULNERABILITY INDEX...',
];


const MONO_FONT = "'JetBrains Mono', 'Fira Code', 'Courier New', monospace";

const BrainSvg = () => (
  <svg
    viewBox="0 0 120 140"
    className="w-20 h-24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ filter: 'drop-shadow(0 0 12px rgba(94,234,212,0.4))' }}
  >
    {/* Head silhouette */}
    <path
      d="M60 130 C60 130 30 115 28 80 C26 55 35 30 60 20 C85 30 94 55 92 80 C90 115 60 130 60 130Z"
      stroke="#5eead4"
      strokeWidth="1.5"
      fill="none"
      opacity="0.6"
    />
    {/* Outer brain ring */}
    <circle cx="60" cy="70" r="28" stroke="#5eead4" strokeWidth="1" opacity="0.4" />
    {/* Inner brain ring */}
    <circle cx="60" cy="70" r="18" stroke="#5eead4" strokeWidth="1.2" opacity="0.6" />
    {/* Core */}
    <circle cx="60" cy="70" r="8" stroke="#5eead4" strokeWidth="1.5" opacity="0.8" />
    {/* Center dot */}
    <circle cx="60" cy="70" r="2.5" fill="#5eead4" opacity="0.9" />
    {/* Cross hairs */}
    <line x1="60" y1="58" x2="60" y2="50" stroke="#5eead4" strokeWidth="0.8" opacity="0.4" />
    <line x1="60" y1="82" x2="60" y2="90" stroke="#5eead4" strokeWidth="0.8" opacity="0.4" />
    <line x1="48" y1="70" x2="40" y2="70" stroke="#5eead4" strokeWidth="0.8" opacity="0.4" />
    <line x1="72" y1="70" x2="80" y2="70" stroke="#5eead4" strokeWidth="0.8" opacity="0.4" />
  </svg>
);

const NeuralAnalysisLoader = ({ onComplete }: { onComplete?: () => void }) => {
  const [phraseIndex, setPhraseIndex] = useState(0);

  // Auto-complete after cycling through all phrases
  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete?.();
    }, 3500);
    return () => clearTimeout(timer);
  }, [onComplete]);

  // Cycle status phrases
  useEffect(() => {
    const interval = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % STATUS_PHRASES.length);
    }, 700);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center"
      style={{ background: 'hsl(var(--background))' }}
    >
      {/* Scan-line overlay on card */}
      <style>{`
        @keyframes brainPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes orbitParticle {
          0% { transform: rotate(0deg) translateX(72px) rotate(0deg); }
          100% { transform: rotate(360deg) translateX(72px) rotate(-360deg); }
        }
        @keyframes scanLines {
          0% { background-position: 0 0; }
          100% { background-position: 0 200px; }
        }
        @keyframes fadePhrase {
          0% { opacity: 0; transform: translateY(4px); }
          15% { opacity: 1; transform: translateY(0); }
          85% { opacity: 1; transform: translateY(0); }
          100% { opacity: 0; transform: translateY(-4px); }
        }
        @keyframes terminalFadeIn {
          from { opacity: 0; transform: translateX(-8px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes floatCorner {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
      `}</style>

      {/* Main card */}
      <div
        className="relative flex items-center justify-center"
        style={{
          width: 220,
          height: 220,
          background: 'linear-gradient(180deg, rgba(14,18,30,0.95) 0%, rgba(10,11,16,0.98) 100%)',
          border: '1px solid rgba(94,234,212,0.1)',
          borderRadius: 12,
          boxShadow: '0 0 40px rgba(94,234,212,0.08), 0 0 80px rgba(94,234,212,0.03)',
        }}
      >
        {/* Scan-line effect */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            borderRadius: 12,
            overflow: 'hidden',
            backgroundImage:
              'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(94,234,212,0.015) 3px, rgba(94,234,212,0.015) 4px)',
            backgroundSize: '100% 200px',
            animation: 'scanLines 8s linear infinite',
          }}
        />

        {/* Corner indicators */}
        {[
          { top: -6, left: -6 },
          { top: -6, right: -6 },
          { bottom: -6, left: -6 },
          { bottom: -6, right: -6 },
        ].map((pos, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              ...pos,
              width: 6,
              height: 6,
              background: '#5eead4',
              borderRadius: 1,
              animation: `floatCorner 3s ease-in-out ${i * 0.7}s infinite`,
            } as React.CSSProperties}
          />
        ))}

        {/* Orbit ring */}
        <div
          className="absolute"
          style={{
            width: 144,
            height: 144,
            border: '1px solid rgba(94,234,212,0.15)',
            borderRadius: '50%',
          }}
        >
          {/* Orbiting particle */}
          <div
            className="absolute"
            style={{
              top: '50%',
              left: '50%',
              width: 0,
              height: 0,
              animation: 'orbitParticle 5s linear infinite',
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#5eead4',
                boxShadow: '0 0 8px rgba(94,234,212,0.8), 0 0 16px rgba(94,234,212,0.4)',
                marginTop: -3,
                marginLeft: -3,
              }}
            />
          </div>
        </div>

        {/* Brain icon */}
        <div style={{ animation: 'brainPulse 10s ease-in-out infinite' }}>
          <BrainSvg />
        </div>
      </div>

      {/* Status text */}
      <div className="mt-8 min-h-[3rem] flex items-center justify-center px-6">
        <p
          key={phraseIndex}
          className="text-center"
          style={{
            fontFamily: MONO_FONT,
            fontSize: 'clamp(0.65rem, 2.5vw, 0.8rem)',
            color: '#5eead4',
            letterSpacing: '0.1em',
            animation: 'fadePhrase 0.7s ease-in-out',
            overflowWrap: 'break-word',
          }}
        >
          {STATUS_PHRASES[phraseIndex]}
        </p>
      </div>

      {/* Bottom terminal log */}
    </div>
  );
};

export default NeuralAnalysisLoader;
