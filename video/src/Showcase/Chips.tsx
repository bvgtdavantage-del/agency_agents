import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_FAMILY, PALETTE } from "./constants";

export const Chips: React.FC<{ chips: string[]; startFrame: number }> = ({
  chips,
  startFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", gap: 18 }}>
      {chips.map((chip, i) => {
        const progress = spring({
          frame: frame - startFrame - i * 6,
          fps,
          config: { damping: 14, mass: 0.5, stiffness: 120 },
        });
        return (
          <div
            key={chip}
            style={{
              transform: `scale(${progress})`,
              opacity: progress,
              padding: "14px 28px",
              borderRadius: 999,
              fontFamily: FONT_FAMILY,
              fontSize: 30,
              fontWeight: 500,
              color: PALETTE.text,
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              backdropFilter: "blur(8px)",
            }}
          >
            {chip}
          </div>
        );
      })}
    </div>
  );
};
