import { motion, AnimatePresence } from "framer-motion";

interface Cloud {
  id: number;
  x: number;
  y: number;
  cleared: boolean;
}

const StormClouds = ({ clouds }: { clouds: Cloud[] }) => (
  <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
    <AnimatePresence>
      {clouds.filter(c => !c.cleared).map((cloud) => (
        <motion.div
          key={cloud.id}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{
            opacity: 0,
            scale: 1.3,
            filter: "blur(12px)",
            transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
          }}
          className="absolute"
          style={{ left: `${cloud.x}%`, top: `${cloud.y}%` }}
        >
          <svg width="120" height="60" viewBox="0 0 120 60" fill="none">
            <path
              d="M10 50 L25 15 L40 42 L55 8 L70 38 L85 12 L100 45 L110 25 L120 50Z"
              fill="hsla(0, 40%, 30%, 0.35)"
              stroke="hsla(0, 50%, 40%, 0.4)"
              strokeWidth="1"
            />
            <path
              d="M5 55 L20 28 L35 48 L50 18 L65 44 L80 20 L95 50 L115 35"
              fill="none"
              stroke="hsla(220, 10%, 35%, 0.3)"
              strokeWidth="1.5"
            />
          </svg>
        </motion.div>
      ))}
    </AnimatePresence>
  </div>
);

export default StormClouds;
export type { Cloud };
