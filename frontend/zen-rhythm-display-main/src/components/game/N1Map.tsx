import { motion } from "framer-motion";

interface GlitchMark {
  id: number;
  position: number; // 0-1
  cleared: boolean;
}

const N1Map = ({ marks }: { marks: GlitchMark[] }) => (
  <div className="w-full max-w-md mx-auto px-4">
    <div className="flex items-center gap-1 mb-1">
      <span className="font-mono-game text-[9px] uppercase tracking-[0.15em] text-muted-foreground">
        N1 Map
      </span>
    </div>
    <div className="relative h-2 rounded-full bg-secondary overflow-hidden">
      {/* Track line */}
      <div className="absolute inset-0 bg-gradient-to-r from-secondary via-muted to-secondary" />

      {/* Glitch marks */}
      {marks.map((mark) => (
        <motion.div
          key={mark.id}
          initial={false}
          animate={{
            backgroundColor: mark.cleared
              ? "hsl(168, 80%, 44%)"
              : "hsl(0, 68%, 55%)",
            boxShadow: mark.cleared
              ? "0 0 6px hsla(168, 80%, 44%, 0.6)"
              : "0 0 4px hsla(0, 68%, 55%, 0.5)",
          }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="absolute top-0 h-full rounded-full"
          style={{
            left: `${mark.position * 100}%`,
            width: 6,
            transform: "translateX(-50%)",
          }}
        />
      ))}
    </div>
  </div>
);

export default N1Map;
export type { GlitchMark };
