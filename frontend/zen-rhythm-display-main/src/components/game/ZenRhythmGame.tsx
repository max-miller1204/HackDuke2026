import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import WaveBackground from "./WaveBackground";
import StormClouds, { type Cloud } from "./StormClouds";
import BreathOrb from "./BreathOrb";
import VagalToneMeter from "./VagalToneMeter";
import N1Map, { type GlitchMark } from "./N1Map";
import InstructionsOverlay from "./InstructionsOverlay";

const CYCLE_DURATION = 10000; // 10s = 0.1Hz
const PERFECT_WINDOW = 400; // ±400ms around peak
const SWIPE_THRESHOLD = 50; // px

const initialClouds: Cloud[] = [
  { id: 1, x: 15, y: 18, cleared: false },
  { id: 2, x: 72, y: 12, cleared: false },
  { id: 3, x: 45, y: 25, cleared: false },
  { id: 4, x: 82, y: 30, cleared: false },
  { id: 5, x: 28, y: 8, cleared: false },
];

const initialMarks: GlitchMark[] = [
  { id: 1, position: 0.12, cleared: false },
  { id: 2, position: 0.28, cleared: false },
  { id: 3, position: 0.45, cleared: false },
  { id: 4, position: 0.63, cleared: false },
  { id: 5, position: 0.78, cleared: false },
];

const ZenRhythmGame = () => {
  const navigate = useNavigate();
  const [showInstructions, setShowInstructions] = useState(true);
  const [gameOver, setGameOver] = useState(false);
  const [phase, setPhase] = useState(0);
  const [feedback, setFeedback] = useState<"neutral" | "perfect" | "offbeat">("neutral");
  const [showPulse, setShowPulse] = useState(false);
  const [isChoppy, setIsChoppy] = useState(false);
  const [vagalTone, setVagalTone] = useState(0);
  const [syncScore, setSyncScore] = useState(100);
  const [streak, setStreak] = useState(0);
  const [clouds, setClouds] = useState<Cloud[]>(initialClouds);
  const [marks, setMarks] = useState<GlitchMark[]>(initialMarks);
  const [statusText, setStatusText] = useState("Inhale...");

  const startTimeRef = useRef(performance.now());
  const touchStartY = useRef<number | null>(null);
  const lastActionTime = useRef(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Precise animation loop — only runs when instructions are dismissed
  useEffect(() => {
    if (showInstructions) return;
    startTimeRef.current = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const elapsed = (now - startTimeRef.current) % CYCLE_DURATION;
      const p = elapsed / CYCLE_DURATION;
      setPhase(p);

      // Status text
      if (p < 0.45) setStatusText("Inhale...");
      else if (p < 0.55) setStatusText("Hold...");
      else setStatusText("Exhale...");

      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [showInstructions]);

  // Audio management — play bird sound when game starts, stop when instructions/menu visible
  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio("/birdSound.mp3");
      audioRef.current.loop = true;
      audioRef.current.volume = 0.5;
    }

    if (!showInstructions && !gameOver) {
      audioRef.current.play().catch(() => {
        // Autoplay might be blocked, ignore
      });
    } else {
      audioRef.current.pause();
    }

    return () => {
      audioRef.current?.pause();
    };
  }, [showInstructions, gameOver]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    };
  }, []);

  const clearNextCloud = useCallback(() => {
    setClouds((prev) => {
      const idx = prev.findIndex((c) => !c.cleared);
      if (idx === -1) return prev;
      const updated = prev.map((c, i) => (i === idx ? { ...c, cleared: true } : c));
      if (updated.every((c) => c.cleared)) {
        setVagalTone(1);
        setTimeout(() => {
          setGameOver(true);
        }, 650);
      }
      return updated;
    });
    setMarks((prev) => {
      const idx = prev.findIndex((m) => !m.cleared);
      if (idx === -1) return prev;
      return prev.map((m, i) => (i === idx ? { ...m, cleared: true } : m));
    });
  }, []);

  const handlePerfect = useCallback(() => {
    setFeedback("perfect");
    setShowPulse(true);
    setIsChoppy(false);
    setStreak((s) => s + 1);
    setVagalTone((v) => Math.min(1, v + 0.12));
    setSyncScore((s) => Math.min(100, s + 2));
    clearNextCloud();
    setTimeout(() => {
      setFeedback("neutral");
      setShowPulse(false);
    }, 1000);
  }, [clearNextCloud]);

  const handleOffbeat = useCallback(() => {
    setFeedback("offbeat");
    setIsChoppy(true);
    setStreak(0);
    setVagalTone((v) => Math.max(0, v - 0.08));
    setSyncScore((s) => Math.max(0, s - 5));
    setTimeout(() => {
      setFeedback("neutral");
      setIsChoppy(false);
    }, 600);
  }, []);

  const checkTapTiming = useCallback(() => {
    const now = performance.now();
    if (now - lastActionTime.current < 800) return; // debounce
    lastActionTime.current = now;

    const elapsed = (now - startTimeRef.current) % CYCLE_DURATION;
    const distFromPeak = Math.abs(elapsed - CYCLE_DURATION / 2);
    if (distFromPeak < PERFECT_WINDOW) {
      handlePerfect();
    } else {
      handleOffbeat();
    }
  }, [handlePerfect, handleOffbeat]);

  const handleSwipe = useCallback(() => {
    const now = performance.now();
    if (now - lastActionTime.current < 800) return;
    lastActionTime.current = now;

    const elapsed = (now - startTimeRef.current) % CYCLE_DURATION;
    // Exhale phase: 5000-10000ms
    if (elapsed > 4600 && elapsed <= 10000) {
      handlePerfect();
    } else {
      handleOffbeat();
    }
  }, [handlePerfect, handleOffbeat]);

  // Keyboard support
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        checkTapTiming();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [checkTapTiming]);

  const onPointerDown = (e: React.PointerEvent) => {
    touchStartY.current = e.clientY;
  };

  const onPointerUp = (e: React.PointerEvent) => {
    if (touchStartY.current !== null) {
      const dy = e.clientY - touchStartY.current;
      if (dy > SWIPE_THRESHOLD) {
        handleSwipe();
      } else {
        checkTapTiming();
      }
      touchStartY.current = null;
    }
  };

  return (
    <div
      className="fixed inset-0 select-none cursor-pointer overflow-hidden"
      style={{ background: "hsl(228, 28%, 6%)" }}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
    >
      <WaveBackground isChoppy={isChoppy} />
      <StormClouds clouds={clouds} />

      {/* UI Layer */}
      <div className="relative z-10 flex flex-col h-full" style={{ touchAction: "none" }}>
        {/* Navbar */}
        <nav className="flex items-center px-6 py-3 mb-8">
          <span
            onClick={(e) => { e.stopPropagation(); navigate('/'); }}
            className="cursor-pointer"
            style={{
              fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
              fontSize: '0.95rem',
              fontWeight: 700,
              color: 'rgba(255,255,255,0.85)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase' as const,
            }}
          >
            SleepFM Clinical
          </span>
        </nav>

        {/* Top bar */}
        <div className="flex items-start justify-between px-6 pb-6">
          {/* Vagal Tone Meter */}
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <VagalToneMeter value={vagalTone} />
          </motion.div>

          {/* Stability Score */}
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col items-center"
          >
            <span className="font-mono-game text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-1">
              Sync
            </span>
            <div className="font-mono-game text-4xl font-light tracking-tight text-foreground">
              {Math.round(syncScore)}
              <span className="text-lg text-muted-foreground">%</span>
            </div>
            {streak > 2 && (
              <motion.span
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="font-mono-game text-[10px] text-glow-teal mt-1"
              >
                ×{streak} streak
              </motion.span>
            )}
          </motion.div>

          {/* Help button */}
          <motion.button
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            whileTap={{ scale: 0.92 }}
            onClick={(e) => {
              e.stopPropagation();
              setShowInstructions(true);
            }}
            className="w-8 h-8 flex items-center justify-center rounded-full font-mono-game text-xs text-muted-foreground hover:text-foreground transition-colors"
            style={{
              background: "hsla(230, 18%, 14%, 0.6)",
              border: "1px solid hsla(230, 16%, 24%, 0.5)",
            }}
          >
            ?
          </motion.button>
        </div>

        {/* Center: Breath Orb */}
        <div className="flex-1 flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 1, ease: [0.16, 1, 0.3, 1] }}
          >
            <BreathOrb phase={phase} feedbackState={feedback} showPulse={showPulse} />
          </motion.div>
        </div>

        {/* Bottom section */}
        <div className="flex flex-col items-center gap-5 pb-16 md:pb-8">
          {/* Status Text */}
          <AnimatePresence mode="wait">
            <motion.p
              key={statusText}
              initial={{ opacity: 0, y: 6, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -6, filter: "blur(4px)" }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="font-mono-game text-sm tracking-[0.3em] uppercase text-muted-foreground"
            >
              {statusText}
            </motion.p>
          </AnimatePresence>

          {/* Tap hint */}
          <p className="text-[10px] text-muted-foreground/50 tracking-widest uppercase">
            Tap at peak · Swipe down on exhale
          </p>

          {/* N1 Map */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="w-full"
          >
            <N1Map marks={marks} />
          </motion.div>
        </div>
      </div>

      {/* Instructions overlay */}
      <AnimatePresence>
        {showInstructions && (
          <InstructionsOverlay onStart={() => setShowInstructions(false)} />
        )}
      </AnimatePresence>

      {/* Game Over overlay */}
      <AnimatePresence>
        {gameOver && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center"
            style={{ background: 'hsla(228, 28%, 6%, 0.92)', backdropFilter: 'blur(12px)' }}
          >
            <motion.div
              initial={{ opacity: 0, y: 20, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ delay: 0.3, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col items-center gap-6"
            >
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{
                  background: 'hsla(var(--primary), 0.1)',
                  boxShadow: '0 0 32px hsla(var(--primary), 0.2)',
                }}
              >
                <span className="text-3xl">✦</span>
              </div>

              <h2
                className="text-2xl md:text-3xl font-bold text-foreground text-center"
                style={{ fontFamily: "'Inter', sans-serif" }}
              >
                Thank You for Playing
              </h2>
              <p
                className="text-sm text-muted-foreground text-center max-w-xs"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                All neural glitches cleared. Your vagal tone has been recalibrated.
              </p>

              <div className="flex flex-col gap-3 mt-4 w-64">
                <button
                  onClick={() => navigate('/results')}
                  className="w-full py-3 rounded-xl text-sm font-bold uppercase tracking-widest transition-all duration-200 active:scale-[0.97]"
                  style={{
                    background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(168, 80%, 44%))',
                    color: 'hsl(var(--primary-foreground))',
                    fontFamily: "'Inter', sans-serif",
                    letterSpacing: '0.12em',
                    boxShadow: '0 0 24px hsla(var(--primary), 0.3)',
                  }}
                >
                  View Results
                </button>
                <button
                  onClick={() => {
                    setGameOver(false);
                    setClouds(initialClouds.map(c => ({ ...c, cleared: false })));
                    setMarks(initialMarks.map(m => ({ ...m, cleared: false })));
                    setVagalTone(0);
                    setSyncScore(100);
                    setStreak(0);
                    startTimeRef.current = performance.now();
                  }}
                  className="w-full py-3 rounded-xl text-sm font-medium uppercase tracking-widest transition-all duration-200 active:scale-[0.97]"
                  style={{
                    background: 'hsla(var(--secondary), 0.8)',
                    color: 'hsl(var(--foreground))',
                    fontFamily: "'Inter', sans-serif",
                    letterSpacing: '0.12em',
                    border: '1px solid hsl(var(--border))',
                  }}
                >
                  Play Again
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ZenRhythmGame;
