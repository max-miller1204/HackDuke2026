import { Upload } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import NeuralAnalysisLoader from './NeuralAnalysisLoader';

const UploadSection = () => {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<'upload' | 'loading'>('upload');
  const [visible, setVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (phase === 'loading') {
    return <NeuralAnalysisLoader onComplete={() => navigate('/results')} />;
  }

  const stagger = (i: number): React.CSSProperties => ({
    transition: 'opacity 0.6s ease-out, transform 0.6s ease-out, filter 0.6s ease-out',
    transitionDelay: visible ? `${i * 150}ms` : '0ms',
    opacity: visible ? 1 : 0,
    transform: visible ? 'translateY(0)' : 'translateY(24px)',
    filter: visible ? 'blur(0px)' : 'blur(4px)',
  });

  return (
    <section
      ref={sectionRef}
      id="upload-section"
      className="min-h-screen flex flex-col items-center justify-center px-6 py-24"
      style={{ background: 'hsl(var(--background))' }}
    >
      {/* Title */}
      <h2
        className="text-center mb-4"
        style={{
          ...stagger(0),
          fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
          fontSize: 'clamp(2rem, 5vw, 3.5rem)',
          fontWeight: 800,
          fontStyle: 'italic',
          textTransform: 'uppercase',
          letterSpacing: '-0.02em',
          lineHeight: 1,
        }}
      >
        <span style={{ color: 'rgba(255,255,255,0.9)' }}>Upload Your </span>
        <span style={{ color: '#5eead4' }}>Sleep Data</span>
      </h2>

      {/* Subtitle */}
      <p
        className="text-center max-w-lg mb-12"
        style={{
          ...stagger(1),
          fontFamily: "'Inter', sans-serif",
          fontSize: 'clamp(0.8rem, 1.5vw, 0.95rem)',
          color: 'rgba(255,255,255,0.5)',
          lineHeight: 1.6,
        }}
      >
        Turn your night signals into a plan of action. Connect your clinical
        wearable or upload your diagnostic raw files for neural wave repair.
      </p>

      {/* Drop zone */}
      <div
        className="w-full max-w-xl rounded-xl p-[1px]"
        style={{
          ...stagger(2),
          background: 'linear-gradient(135deg, rgba(94,234,212,0.2), rgba(94,234,212,0.05), rgba(255,255,255,0.05))',
        }}
      >
        <div
          className="rounded-xl flex flex-col items-center justify-center py-16 px-8 transition-all duration-300 hover:scale-[1.03] hover:shadow-[0_0_30px_rgba(94,234,212,0.15)]"
          style={{
            background: 'linear-gradient(180deg, hsl(216, 18%, 11%) 0%, hsl(var(--background)) 100%)',
            border: '1px dashed rgba(94,234,212,0.15)',
          }}
        >
          {/* Icon */}
          <div
            className="w-12 h-12 rounded-lg flex items-center justify-center mb-5"
            style={{ background: 'rgba(94,234,212,0.1)' }}
          >
            <Upload className="w-5 h-5" style={{ color: '#5eead4' }} />
          </div>

          {/* Drop text */}
          <p
            className="mb-2"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '1rem',
              fontWeight: 600,
              color: 'rgba(255,255,255,0.85)',
            }}
          >
            Drop sleep diagnostic files here
          </p>
          <p
            className="mb-6"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '0.8rem',
              color: 'rgba(255,255,255,0.4)',
            }}
          >
            Supports .EDF, .JSON, and .CSV from validated clinical devices
          </p>

          {/* Badges */}
          <div className="flex gap-3">
            <span
              className="px-3 py-1 rounded-full text-xs font-medium"
              style={{
                background: 'rgba(94,234,212,0.08)',
                color: 'rgba(94,234,212,0.7)',
                border: '1px solid rgba(94,234,212,0.15)',
              }}
            >
              MAX 500MB
            </span>
            <span
              className="px-3 py-1 rounded-full text-xs font-medium"
              style={{
                background: 'rgba(94,234,212,0.08)',
                color: 'rgba(94,234,212,0.7)',
                border: '1px solid rgba(94,234,212,0.15)',
              }}
            >
              SECURE 256-BIT
            </span>
          </div>
        </div>
      </div>

      {/* CTA Button */}
      <button
        className="mt-10 px-8 py-3 rounded-full font-semibold text-sm transition-all duration-200 active:scale-[0.97]"
        style={{
          ...stagger(3),
          background: 'linear-gradient(135deg, #5eead4, #2dd4bf)',
          color: 'hsl(var(--background))',
          fontFamily: "'Inter', sans-serif",
          letterSpacing: '0.02em',
          boxShadow: '0 0 24px rgba(94,234,212,0.25)',
        }}
        onMouseEnter={(e) => {
          (e.target as HTMLElement).style.boxShadow = '0 0 32px rgba(94,234,212,0.4)';
        }}
        onMouseLeave={(e) => {
          (e.target as HTMLElement).style.boxShadow = '0 0 24px rgba(94,234,212,0.25)';
        }}
        onClick={() => setPhase('loading')}
      >
        Start Analysis
      </button>
    </section>
  );
};

export default UploadSection;
