import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useAspect, useTexture } from '@react-three/drei';
import { useMemo, useRef, useState, useEffect, Suspense } from 'react';
import { useIsMobile } from '@/hooks/use-mobile';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';


const TEXTUREMAP_SRC = 'https://i.postimg.cc/XYwvXN8D/img-4.png';
const DEPTHMAP_SRC = 'https://i.postimg.cc/2SHKQh2q/raw-4.webp';


// Main scene vertex/fragment shaders (replaces TSL node material)
const sceneVertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const sceneFragmentShader = `
  uniform sampler2D uColorMap;
  uniform sampler2D uDepthMap;
  uniform vec2 uPointer;
  uniform float uProgress;
  uniform float uOpacity;

  varying vec2 vUv;

  // Simple cell noise approximation
  float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }

  float cellNoise(vec2 p) {
    vec2 i = floor(p);
    return hash(i);
  }

  void main() {
    float depth = texture2D(uDepthMap, vUv).r;
    
    // Parallax offset
    float strength = 0.01;
    vec2 offset = depth * uPointer * strength;
    vec4 color = texture2D(uColorMap, vUv + offset);
    
    // Halftone dot pattern
    float aspect = 1.0; // square texture
    vec2 tUv = vec2(vUv.x * aspect, vUv.y);
    vec2 tiling = vec2(120.0);
    vec2 tiledUv = mod(tUv * tiling, 2.0) - 1.0;
    
    float brightness = cellNoise(tUv * tiling * 0.5);
    float dist = length(tiledUv);
    float dot = step(dist, 0.5) * brightness;
    
    // Flow / scan effect
    float flow = 1.0 - smoothstep(0.0, 0.02, abs(depth - uProgress));
    
    vec3 mask = vec3(dot * flow) * vec3(0.0, 10.0, 8.0);
    
    // Blend screen
    vec3 finalColor = 1.0 - (1.0 - color.rgb) * (1.0 - mask);
    
    gl_FragColor = vec4(finalColor, uOpacity);
  }
`;

const PostProcessing = () => {
  const { gl, scene, camera, size } = useThree();
  const composerRef = useRef<EffectComposer | null>(null);

  useEffect(() => {
    const composer = new EffectComposer(gl);
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);

    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(size.width, size.height),
      1.0, // strength
      0.5, // radius
      1.0 // threshold
    );
    composer.addPass(bloomPass);

    composerRef.current = composer;

    return () => {
      composer.dispose();
    };
  }, [gl, scene, camera, size]);

  useEffect(() => {
    if (composerRef.current) {
      composerRef.current.setSize(size.width, size.height);
    }
  }, [size]);

  useFrame(() => {
    if (composerRef.current) {
      composerRef.current.render();
    }
  }, 1);

  return null;
};

const WIDTH = 300;
const HEIGHT = 300;

const Scene = () => {
  const [rawMap, depthMap] = useTexture([TEXTUREMAP_SRC, DEPTHMAP_SRC]);
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const [visible, setVisible] = useState(false);
  const pointerRef = useRef(new THREE.Vector2(0, 0));

  useEffect(() => {
    if (rawMap && depthMap) {
      setVisible(true);
    }
  }, [rawMap, depthMap]);

  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uColorMap: { value: rawMap },
        uDepthMap: { value: depthMap },
        uPointer: { value: new THREE.Vector2(0, 0) },
        uProgress: { value: 0 },
        uOpacity: { value: 0 }
      },
      vertexShader: sceneVertexShader,
      fragmentShader: sceneFragmentShader,
      transparent: true
    });
  }, [rawMap, depthMap]);

  useEffect(() => {
    materialRef.current = material;
  }, [material]);

  const [w, h] = useAspect(WIDTH, HEIGHT);

  useFrame(({ clock, pointer }) => {
    if (!materialRef.current) return;
    materialRef.current.uniforms.uProgress.value =
    Math.sin(clock.getElapsedTime() * 0.5) * 0.5 + 0.5;

    // Smooth pointer follow
    pointerRef.current.lerp(pointer, 0.05);
    materialRef.current.uniforms.uPointer.value.copy(pointerRef.current);

    // Fade in
    const target = visible ? 1 : 0;
    materialRef.current.uniforms.uOpacity.value = THREE.MathUtils.lerp(
      materialRef.current.uniforms.uOpacity.value,
      target,
      0.07
    );
  });

  const scaleFactor = 0.4;

  return (
    <mesh ref={meshRef} scale={[w * scaleFactor, h * scaleFactor, 1]} material={material}>
      <planeGeometry args={[1, 1]} />
    </mesh>);

};

const FallbackLoader = () =>
<div className="absolute inset-0 flex items-center justify-center">
    <div
    className="w-8 h-8 rounded-full animate-pulse"
    style={{ background: 'hsla(var(--glow-teal), 0.3)' }} />
  
  </div>;


export interface HeroFuturisticProps {
  title?: string;
  subtitle?: string;
  children?: React.ReactNode;
}

export const HeroFuturistic = ({
  title = 'Build Your Dreams',
  subtitle = 'AI-powered creativity for the next generation.',
  children
}: HeroFuturisticProps) => {
  const isMobile = useIsMobile();
  // Split title into ~2 words per line on mobile, ~3 lines on desktop
  const titleWords = title.split(' ');
  const wordsPerLine = isMobile ? 2 : Math.ceil(titleWords.length / 3);
  const titleLines = [];
  for (let i = 0; i < titleWords.length; i += wordsPerLine) {
    titleLines.push(titleWords.slice(i, i + wordsPerLine).join(' '));
  }

  const [titleVisible, setTitleVisible] = useState(false);
  const [subtitleVisible, setSubtitleVisible] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setTitleVisible(true), 300);
    const t2 = setTimeout(() => setSubtitleVisible(true), 1100);
    return () => {clearTimeout(t1);clearTimeout(t2);};
  }, []);

  return (
    <div className="relative w-full h-screen overflow-hidden" style={{ background: '#000' }}>
      {/* Navbar */}
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center px-6 py-4">
        <span
          style={{
            fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
            fontSize: '0.95rem',
            fontWeight: 700,
            color: 'rgba(255,255,255,0.85)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase'
          }}>
          
          SleepFM Clinical
        </span>
      </nav>

      {/* Text overlay */}
      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none">
        <div className="flex flex-col items-center gap-4 px-[50px]">
          {/* Title */}
          <h1 className="flex flex-col items-center gap-1 leading-none text-center">
            {titleLines.map((line, index) =>
            <span
              key={index}
              className="block transition-all duration-700"
              style={{
                opacity: titleVisible ? 1 : 0,
                transform: titleVisible ? 'translateY(0)' : 'translateY(20px)',
                filter: titleVisible ? 'blur(0px)' : 'blur(8px)',
                transitionDelay: `${index * 0.15}s`,
                fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
                fontSize: 'clamp(2rem, 6vw, 4.5rem)',
                fontWeight: 900,
                fontStyle: 'italic',
                color: '#fff',
                letterSpacing: '-0.02em',
                lineHeight: 0.9,
                textTransform: 'uppercase',
                textShadow: '0 0 20px rgba(255,255,255,0.15), 0 2px 4px rgba(0,0,0,0.8)'
              }}>
              
                {line.split(/(Personal Brain)/i).map((part, pi) =>
              /personal brain/i.test(part) ?
              <span key={pi} style={{ color: 'hsl(var(--primary))' }}>{part}</span> :

              <span key={pi}>{part}</span>

              )}
              </span>
            )}
          </h1>

          {/* Subtitle */}
          <p
            className="transition-all duration-700 text-center"
            style={{
              opacity: subtitleVisible ? 1 : 0,
              transform: subtitleVisible ? 'translateY(0)' : 'translateY(10px)',
              filter: subtitleVisible ? 'blur(0px)' : 'blur(4px)',
              fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
              fontSize: 'clamp(0.85rem, 2vw, 1.15rem)',
              fontWeight: 500,
              color: 'rgba(255,255,255,0.9)',
              letterSpacing: '0.12em',
              textTransform: 'none',
              textShadow: '0 0 30px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.8)'
            }}>
            
            {subtitle}
          </p>
        </div>

        {/* Children (e.g. CTA buttons) */}
        {children &&
        <div className="mt-8 pointer-events-auto">
            {children}
          </div>
        }
      </div>

      {/* Scroll indicator */}
      <div
        className="absolute bottom-24 left-1/2 -translate-x-1/2 z-10 flex flex-col md:flex-row items-center gap-1.5 md:gap-3 px-6 py-2.5 md:py-3 rounded-full pointer-events-auto cursor-pointer group transition-all duration-300 hover:scale-105 active:scale-[0.97]"
        style={{
          border: '1px solid rgba(94,234,212,0.2)',
          background: 'rgba(94,234,212,0.03)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(94,234,212,0.45)';
          e.currentTarget.style.background = 'rgba(94,234,212,0.08)';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(94,234,212,0.15), inset 0 0 12px rgba(94,234,212,0.05)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'rgba(94,234,212,0.2)';
          e.currentTarget.style.background = 'rgba(94,234,212,0.03)';
          e.currentTarget.style.boxShadow = 'none';
        }}
        onClick={() => {
          document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth' });
        }}>
        
        <span
          className="transition-colors duration-300 whitespace-nowrap"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '0.85rem',
            color: 'rgba(255,255,255,0.7)',
            letterSpacing: '0.05em'
          }}>
          
          Upload your sleep data
        </span>
        <svg
          className="transition-transform duration-300 group-hover:translate-y-1"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="rgba(94,234,212,0.7)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round">
          
          <path d="M12 5v14" />
          <path d="m19 12-7 7-7-7" />
        </svg>
      </div>

      {/* 3D Canvas */}
      <div className="absolute inset-0">
        <Suspense fallback={<FallbackLoader />}>
          <Canvas
            gl={{ antialias: true, alpha: true }}
            camera={{ position: [0, 0, 5], fov: 50 }}
            style={{ background: 'transparent' }} className="bg-primary-foreground">
            
            <Scene />
            <PostProcessing />
          </Canvas>
        </Suspense>
      </div>
    </div>);

};

export default HeroFuturistic;