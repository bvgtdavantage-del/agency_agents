import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_FAMILY, PALETTE } from "./constants";

export const AnimatedTitle: React.FC<{
  text: string;
  startFrame: number;
  accentFrom: string;
  accentTo: string;
}> = ({ text, startFrame, accentFrom, accentTo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");

  const lineProgress = spring({
    frame: frame - startFrame - words.length * 4 - 6,
    fps,
    config: { damping: 200, mass: 0.6 },
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          maxWidth: 1400,
          fontFamily: FONT_FAMILY,
          fontSize: 156,
          fontWeight: 700,
          letterSpacing: "-0.03em",
          lineHeight: 1.02,
          color: PALETTE.text,
        }}
      >
        {words.map((word, i) => {
          const progress = spring({
            frame: frame - startFrame - i * 4,
            fps,
            config: { damping: 200, mass: 0.7 },
          });
          const y = interpolate(progress, [0, 1], [46, 0]);
          const blur = interpolate(progress, [0, 1], [12, 0]);
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                marginRight: "0.26em",
                transform: `translateY(${y}px)`,
                opacity: progress,
                filter: `blur(${blur}px)`,
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
      <div
        style={{
          marginTop: 34,
          height: 5,
          width: 260,
          borderRadius: 999,
          background: `linear-gradient(90deg, ${accentFrom}, ${accentTo})`,
          transform: `scaleX(${lineProgress})`,
          transformOrigin: "left center",
          opacity: interpolate(lineProgress, [0, 0.2], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      />
    </div>
  );
};
