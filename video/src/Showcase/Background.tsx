import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { PALETTE } from "./constants";

const Blob: React.FC<{
  color: string;
  size: number;
  baseX: number;
  baseY: number;
  ampX: number;
  ampY: number;
  speed: number;
  phase: number;
  seconds: number;
}> = ({ color, size, baseX, baseY, ampX, ampY, speed, phase, seconds }) => {
  const x = baseX + Math.sin(seconds * speed + phase) * ampX;
  const y = baseY + Math.cos(seconds * speed * 0.8 + phase) * ampY;
  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        transform: "translate(-50%, -50%)",
        borderRadius: "50%",
        background: `radial-gradient(circle, ${color} 0%, transparent 68%)`,
        filter: "blur(90px)",
        mixBlendMode: "screen",
      }}
    />
  );
};

export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;

  const intro = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: PALETTE.base }}>
      <AbsoluteFill style={{ opacity: intro }}>
        <Blob color={PALETTE.indigo} size={1100} baseX={28} baseY={34} ampX={5} ampY={6} speed={0.35} phase={0} seconds={seconds} />
        <Blob color={PALETTE.violet} size={1000} baseX={74} baseY={30} ampX={6} ampY={5} speed={0.28} phase={2.1} seconds={seconds} />
        <Blob color={PALETTE.cyan} size={900} baseX={60} baseY={78} ampX={7} ampY={5} speed={0.32} phase={4.2} seconds={seconds} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 45%, black 30%, transparent 78%)",
          WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 50% 45%, black 30%, transparent 78%)",
          opacity: intro * 0.9,
        }}
      />

      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse 90% 80% at 50% 50%, transparent 55%, rgba(0,0,0,0.55) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
