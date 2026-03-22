import { motion } from "framer-motion";

const VagalToneMeter = ({ value }: { value: number }) => {
  const segments = 20;
  const filled = Math.round(value * segments);

  return (
    <div className="flex flex-col items-center gap-2">
      <span className="font-mono-game text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        Vagal
      </span>
      <div className="relative flex flex-col-reverse gap-[3px]">
        {Array.from({ length: segments }).map((_, i) => {
          const active = i < filled;
          const hue = 174 + (i / segments) * -6; // subtle shift
          return (
            <motion.div
              key={i}
              initial={false}
              animate={{
                opacity: active ? 1 : 0.15,
                scaleX: active ? 1 : 0.7,
              }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="rounded-sm"
              style={{
                width: 8,
                height: 6,
                backgroundColor: active
                  ? `hsl(${hue}, 72%, ${48 + (i / segments) * 12}%)`
                  : "hsl(230, 16%, 22%)",
                boxShadow: active ? `0 0 6px hsla(${hue}, 72%, 52%, 0.4)` : "none",
              }}
            />
          );
        })}
      </div>
      <span className="font-mono-game text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        Tone
      </span>
    </div>
  );
};

export default VagalToneMeter;
