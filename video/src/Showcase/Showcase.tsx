import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { AnimatedTitle } from "./AnimatedTitle";
import { Background } from "./Background";
import { Chips } from "./Chips";
import { FONT_FAMILY, PALETTE } from "./constants";

export const showcaseSchema = z.object({
  kicker: z.string(),
  titleText: z.string(),
  subtitle: z.string(),
  chips: z.array(z.string()),
  accentFrom: zColor(),
  accentTo: zColor(),
});

const Kicker: React.FC<{ text: string; accentFrom: string }> = ({ text, accentFrom }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 14], [14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        display: "flex",
        alignItems: "center",
        gap: 14,
        fontFamily: FONT_FAMILY,
        fontSize: 26,
        fontWeight: 600,
        letterSpacing: "0.32em",
        color: PALETTE.muted,
      }}
    >
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: accentFrom }} />
      {text}
    </div>
  );
};

const Subtitle: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 16], [18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        fontFamily: FONT_FAMILY,
        fontSize: 40,
        fontWeight: 400,
        color: PALETTE.muted,
        maxWidth: 900,
        textAlign: "center",
      }}
    >
      {text}
    </div>
  );
};

export const Showcase: React.FC<z.infer<typeof showcaseSchema>> = ({
  kicker,
  titleText,
  subtitle,
  chips,
  accentFrom,
  accentTo,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 22, durationInFrames - 6],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const exitScale = interpolate(
    frame,
    [durationInFrames - 22, durationInFrames - 6],
    [1, 1.04],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          opacity: exitOpacity,
          transform: `scale(${exitScale})`,
          alignItems: "center",
          justifyContent: "center",
          gap: 44,
        }}
      >
        <Sequence from={10} layout="none">
          <Kicker text={kicker} accentFrom={accentFrom} />
        </Sequence>
        <Sequence from={24} layout="none">
          <AnimatedTitle
            text={titleText}
            startFrame={0}
            accentFrom={accentFrom}
            accentTo={accentTo}
          />
        </Sequence>
        <Sequence from={70} layout="none">
          <Subtitle text={subtitle} />
        </Sequence>
        <Sequence from={92} layout="none">
          <Chips chips={chips} startFrame={0} />
        </Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
