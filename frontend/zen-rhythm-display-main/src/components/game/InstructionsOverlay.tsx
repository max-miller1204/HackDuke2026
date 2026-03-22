import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

interface InstructionsOverlayProps {
  onStart: () => void;
}

const DEMO_CYCLE = 6000; // faster cycle for demo

const MiniOrb = () => {
  const [phase, setPhase] = useState(0);
  const startRef = useRef(performance.now());

  useEffect(() => {
    let raf: number;
    const tick = (now: number) => {
      const p = (now - startRef.current) % DEMO_CYCLE / DEMO_CYCLE;
      setPhase(p);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const scale = phase <= 0.5 ? 0.5 + phase * 1.0 : 1.0 - (phase - 0.5) * 1.0;
  const brightness = phase <= 0.5 ? 0.4 + phase * 1.2 : 1.0 - (phase - 0.5) * 1.2;
  const isPeak = Math.abs(phase - 0.5) < 0.08;
  const isExhale = phase > 0.55;

  return (
    <div className="relative flex items-center justify-center" style={{ width: 140, height: 140 }}>
      {/* Ambient pulsing glow */}
      <motion.div
        className="absolute rounded-full"
        animate={{
          scale: [1, 1.3, 1],
          opacity: [0.3, 0.6, 0.3]
        }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        style={{
          width: 140,
          height: 140,
          background: `radial-gradient(circle, hsl(160, 90%, 55%, 0.25) 0%, hsl(168, 85%, 48%, 0.08) 50%, transparent 70%)`,
          filter: "blur(20px)"
        }} />
      
      {/* Outer glow ring */}
      <div
        className="absolute rounded-full"
        style={{
          width: 130 * scale,
          height: 130 * scale,
          background: `radial-gradient(circle, hsl(160, 95%, 55%, 0.3) 0%, transparent 65%)`,
          filter: `blur(${18 * brightness}px)`
        }} />
      
      {/* Core orb */}
      <div
        className="rounded-full"
        style={{
          width: 90 * scale,
          height: 90 * scale,
          background: `radial-gradient(circle at 38% 32%, hsl(160, 95%, 60%, 1), hsl(168, 90%, 50%, 0.7) 55%, hsl(174, 80%, 40%, 0.3) 80%, transparent)`,
          boxShadow: `
            0 0 ${40 * brightness}px hsl(160, 95%, 55%, 0.6),
            0 0 ${80 * brightness}px hsl(168, 85%, 48%, 0.25),
            inset 0 0 ${20 * brightness}px hsl(160, 90%, 65%, 0.3)
          `
        }} />
      
      {/* Peak indicator */}
      {isPeak &&
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1.8, opacity: [0.7, 0] }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="absolute rounded-full border border-primary"
        style={{ width: 56, height: 56 }} />

      }
      {/* Exhale arrow */}
      {isExhale &&
      <motion.div
        className="absolute -right-10 top-1/2 -translate-y-1/2"
        animate={{ y: [0, 6, 0] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}>
        
          <svg width="20" height="24" viewBox="0 0 20 24" fill="none">
            <path d="M10 2 L10 20 M4 14 L10 22 L16 14" stroke="hsl(var(--muted-foreground))" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.div>
      }
    </div>);

};

const steps = [
{
  label: "Breathe",
  description: "Follow the orb's rhythm. It expands on inhale and contracts on exhale — one full cycle every 10 seconds."
},
{
  label: "Tap at Peak",
  description: "Tap the screen or press Space when the orb reaches its maximum size. Timing is everything."
},
{
  label: "Swipe on Exhale",
  description: "Swipe downward during the exhale phase to synchronize your out-breath."
}];


const InstructionsOverlay = ({ onStart }: InstructionsOverlayProps) => {
  const navigate = useNavigate();
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-0 z-50 flex flex-col"
      style={{ background: "hsl(228, 28%, 6%, 0.94)", backdropFilter: "blur(12px)" }}>
      
      {/* Navbar */}
      <nav className="flex items-center px-6 py-3 shrink-0">
        <span
          onClick={(e) => {e.stopPropagation();navigate('/');}}
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

      <div className="flex-1 flex items-center justify-center overflow-hidden py-4 pb-8">
      <motion.div
          initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ delay: 0.15, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col md:flex-row items-center gap-6 md:gap-16 max-w-sm md:max-w-4xl px-6 w-full">
          
        {/* Left column on desktop: title + orb */}
        <div className="flex flex-col items-center gap-4 md:gap-6 md:flex-1">
          {/* Title */}
          <div className="flex flex-col items-center gap-1 text-sm">
            <h1
                className="md:text-4xl tracking-tight text-foreground text-3xl font-semibold"
                style={{ fontFamily: "Arial, Helvetica, sans-serif", textShadow: "0 0 24px hsl(var(--glow-cyan) / 0.35)" }}>
              Zen Rhythm
            </h1>
            <p className="md:text-sm tracking-[0.25em] uppercase text-muted-foreground text-base font-semibold"
              style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
              How to play
            </p>
          </div>

          {/* Live mini-orb preview */}
          <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.4, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="flex items-center justify-center py-1 md:py-8">
              
            <MiniOrb />
          </motion.div>

          {/* Scoring note — desktop only here */}
          <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9, duration: 0.5 }}
              className="hidden md:block text-xs text-center leading-relaxed text-muted-foreground/70 max-w-[340px]">
              
            Perfect timing builds your Sync Score and Vagal Tone.
            Clear all storm clouds to restore calm.
          </motion.p>
        </div>

        {/* Right column on desktop: steps + button */}
        <div className="flex flex-col items-center md:items-start gap-6 md:gap-8 md:flex-1">
          {/* Steps */}
          <div className="flex flex-col gap-4 md:gap-6 w-full text-base">
            {steps.map((step, i) =>
              <motion.div
                key={step.label}
                initial={{ opacity: 0, x: -12, filter: "blur(4px)" }}
                animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
                transition={{
                  delay: 0.5 + i * 0.12,
                  duration: 0.6,
                  ease: [0.16, 1, 0.3, 1]
                }}
                className="flex gap-3 md:gap-4 items-start">
                
                <span
                  className="text-xs md:text-sm font-medium text-primary mt-0.5 shrink-0 w-5 h-5 md:w-7 md:h-7 flex items-center justify-center rounded-full"
                  style={{
                    fontFamily: "Arial, Helvetica, sans-serif",
                    background: "hsl(var(--glow-cyan) / 0.12)",
                    boxShadow: "0 0 8px hsl(var(--glow-cyan) / 0.15)"
                  }}>
                  
                  {i + 1}
                </span>
                <div className="flex flex-col gap-0.5 md:gap-1">
                  <span className="tracking-wide text-foreground text-base md:text-2xl" style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
                    {step.label}
                  </span>
                  <span className="md:text-sm leading-relaxed text-muted-foreground text-sm" style={{ fontFamily: "Arial, Helvetica, sans-serif" }}>
                    {step.description}
                  </span>
                </div>
              </motion.div>
              )}
          </div>

          {/* Scoring note — mobile only */}
          <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9, duration: 0.5 }}
              className="md:hidden text-[10px] text-center leading-relaxed text-muted-foreground/70 max-w-[280px]">
              
            Perfect timing builds your Sync Score and Vagal Tone.
            Clear all storm clouds to restore calm.
          </motion.p>

          {/* Begin button */}
          <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.96 }}
              onClick={onStart}
              className="text-sm md:text-base tracking-[0.2em] uppercase px-10 md:px-14 py-3 md:py-4 rounded-full text-primary-foreground transition-shadow duration-200 mb-4 font-bold"
              style={{
                fontFamily: "Arial, Helvetica, sans-serif",
                background: "hsl(var(--glow-cyan))",
                boxShadow: "0 0 20px hsl(var(--glow-cyan) / 0.3), 0 0 60px hsl(var(--glow-cyan) / 0.1)"
              }}>
              
            Begin
          </motion.button>
        </div>
      </motion.div>
      </div>
    </motion.div>);

};

export default InstructionsOverlay;