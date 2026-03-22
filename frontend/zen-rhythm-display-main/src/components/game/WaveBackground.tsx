import { useRef, useEffect } from "react";

const WaveBackground = ({ isChoppy }: { isChoppy: boolean }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const timeRef = useRef(0);
  const choppyRef = useRef(false);
  choppyRef.current = isChoppy;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    let raf: number;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const draw = (timestamp: number) => {
      timeRef.current = timestamp * 0.001;
      const t = timeRef.current;
      const w = canvas.width;
      const h = canvas.height;
      const choppy = choppyRef.current;

      ctx.clearRect(0, 0, w, h);

      // N1 Sleep wave layers
      const layers = [
        { amp: 30, freq: 0.003, speed: 0.3, y: h * 0.55, alpha: 0.12, color: "140, 80%, 40%" },
        { amp: 20, freq: 0.005, speed: 0.5, y: h * 0.6, alpha: 0.08, color: "174, 72%, 52%" },
        { amp: 40, freq: 0.002, speed: 0.2, y: h * 0.65, alpha: 0.06, color: "240, 40%, 30%" },
      ];

      for (const layer of layers) {
        ctx.beginPath();
        const choppyMod = choppy ? Math.sin(t * 8) * 12 : 0;
        for (let x = 0; x <= w; x += 2) {
          const y =
            layer.y +
            Math.sin(x * layer.freq + t * layer.speed) * layer.amp +
            Math.sin(x * layer.freq * 2.3 + t * layer.speed * 1.7) * (layer.amp * 0.4) +
            choppyMod * Math.sin(x * 0.02 + t * 3);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        ctx.fillStyle = `hsla(${layer.color}, ${layer.alpha})`;
        ctx.fill();
      }

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
};

export default WaveBackground;
