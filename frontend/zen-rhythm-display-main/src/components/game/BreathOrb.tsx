import { motion } from "framer-motion";

interface BreathOrbProps {
  /** 0-1 representing position in the 10s cycle. 0-0.5 = inhale, 0.5-1 = exhale */
  phase: number;
  feedbackState: "neutral" | "perfect" | "offbeat";
  showPulse: boolean;
}

const BreathOrb = ({ phase, feedbackState, showPulse }: BreathOrbProps) => {
  const scale =
    phase <= 0.5
      ? 0.6 + phase * 0.8
      : 1.0 - (phase - 0.5) * 0.8;

  const brightness = phase <= 0.5 ? 0.6 + phase * 0.8 : 1.0 - (phase - 0.5) * 0.8;

  const isOffbeat = feedbackState === "offbeat";
  const isPerfect = feedbackState === "perfect";

  const coreHsl = isOffbeat ? "0, 65%, 45%" : "168, 70%, 36%";
  const brightHsl = isOffbeat ? "0, 70%, 50%" : isPerfect ? "162, 80%, 44%" : "166, 72%, 40%";

  return (
    <div className="relative flex items-center justify-center">
      {showPulse && (
        <motion.div
          initial={{ scale: 1, opacity: 0.8 }}
          animate={{ scale: 3, opacity: 0 }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          className="absolute rounded-full"
          style={{
            width: 180,
            height: 180,
            border: `2px solid hsl(${brightHsl})`,
          }}
        />
      )}

      {/* Wide ambient glow */}
      <div
        className="absolute rounded-full"
        style={{
          width: 260 * scale,
          height: 260 * scale,
          background: `radial-gradient(circle, hsla(${coreHsl}, 0.2) 0%, hsla(${coreHsl}, 0.06) 40%, transparent 70%)`,
          filter: `blur(${24 * brightness}px)`,
        }}
      />

      {/* Main orb — solid opaque core */}
      <div
        className="relative rounded-full"
        style={{
          width: 160 * scale,
          height: 160 * scale,
          background: `radial-gradient(circle at 38% 32%, hsl(${brightHsl}), hsl(${coreHsl}) 60%, hsla(${coreHsl}, 0.7) 85%)`,
          boxShadow: `
            0 0 ${40 * brightness}px hsla(${coreHsl}, 0.5),
            0 0 ${80 * brightness}px hsla(${coreHsl}, 0.2),
            inset 0 0 ${25 * brightness}px hsla(${brightHsl}, 0.3)
          `,
        }}
      >
        {/* Specular highlight */}
        <div
          className="absolute rounded-full"
          style={{
            width: "38%",
            height: "38%",
            top: "16%",
            left: "22%",
            background: `radial-gradient(circle, hsla(0, 0%, 100%, ${0.35 * brightness}), transparent)`,
          }}
        />
      </div>

      {/* Flickering effect on offbeat */}
      {feedbackState === "offbeat" && (
        <motion.div
          animate={{ opacity: [0, 0.6, 0, 0.4, 0] }}
          transition={{ duration: 0.4, ease: "linear" }}
          className="absolute rounded-full"
          style={{
            width: 140 * scale,
            height: 140 * scale,
            background: "hsla(0, 68%, 55%, 0.3)",
          }}
        />
      )}
    </div>
  );
};

export default BreathOrb;
