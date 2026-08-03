import { ContactShadows, RoundedBox } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import type { Group, Mesh } from "three";
import { MathUtils } from "three";

import {
  expressionForEmotion,
  type AvatarExpression,
  type ConversationAnimationState,
} from "./expressions";

interface AvatarProps {
  conversationState: ConversationAnimationState;
  emotion: string | null;
}

const SKIN = "#c9825f";
const SKIN_LIGHT = "#e6a47e";
const HAIR = "#172822";
const SHIRT = "#2b8062";
const EYE = "#f8fff8";
const IRIS = "#234c40";
const PUPIL = "#10241f";
const MOUTH = "#6e2d32";
const MOUTH_LIGHT = "#9a4a51";
const EYE_OFFSETS = [-1, 1] as const;
const MOUTH_SEGMENT_COUNT = 17;
const MOUTH_SEGMENT_INDICES = Array.from(
  { length: MOUTH_SEGMENT_COUNT },
  (_, index) => index,
);
const MOUTH_INNER_SEGMENT_INDICES = MOUTH_SEGMENT_INDICES.slice(1, -1);

function dampExpression(
  current: AvatarExpression,
  target: AvatarExpression,
  delta: number,
) {
  const smoothing = 5.5;
  current.browLift = MathUtils.damp(
    current.browLift,
    target.browLift,
    smoothing,
    delta,
  );
  current.browSlant = MathUtils.damp(
    current.browSlant,
    target.browSlant,
    smoothing,
    delta,
  );
  current.eyeOpenness = MathUtils.damp(
    current.eyeOpenness,
    target.eyeOpenness,
    smoothing,
    delta,
  );
  current.headNod = MathUtils.damp(
    current.headNod,
    target.headNod,
    smoothing,
    delta,
  );
  current.headTilt = MathUtils.damp(
    current.headTilt,
    target.headTilt,
    smoothing,
    delta,
  );
  current.mouthCurve = MathUtils.damp(
    current.mouthCurve,
    target.mouthCurve,
    smoothing,
    delta,
  );
  current.mouthOpen = MathUtils.damp(
    current.mouthOpen,
    target.mouthOpen,
    smoothing,
    delta,
  );
  current.mouthWidth = MathUtils.damp(
    current.mouthWidth,
    target.mouthWidth,
    smoothing,
    delta,
  );
}

export function Avatar({ conversationState, emotion }: AvatarProps) {
  const bust = useRef<Group>(null);
  const head = useRef<Group>(null);
  const eyes = useRef<Array<Group | null>>([]);
  const pupils = useRef<Array<Mesh | null>>([]);
  const leftBrow = useRef<Mesh>(null);
  const rightBrow = useRef<Mesh>(null);
  const mouthOpening = useRef<Mesh>(null);
  const upperLip = useRef<Array<Mesh | null>>([]);
  const lowerLip = useRef<Array<Mesh | null>>([]);
  const nextBlink = useRef(2.2);
  const expression = useRef<AvatarExpression>({
    ...expressionForEmotion(emotion),
  });

  const targetExpression = useMemo(
    () => expressionForEmotion(emotion),
    [emotion],
  );

  useFrame(({ clock }, delta) => {
    const elapsed = clock.getElapsedTime();
    dampExpression(expression.current, targetExpression, delta);
    const current = expression.current;

    let blink = 1;
    const blinkProgress = elapsed - nextBlink.current;
    if (blinkProgress >= 0 && blinkProgress < 0.24) {
      blink = 1 - Math.sin((blinkProgress / 0.24) * Math.PI) * 0.96;
    } else if (blinkProgress >= 0.24) {
      nextBlink.current = elapsed + 2.4 + Math.random() * 2.5;
    }

    const thinking = conversationState === "thinking";
    const speaking = conversationState === "speaking";
    const idleSway = Math.sin(elapsed * 0.62) * 0.008;
    const thinkingTilt = thinking ? Math.sin(elapsed * 1.15) * 0.025 + 0.045 : 0;
    const thinkingNod = thinking ? Math.sin(elapsed * 1.8) * 0.018 : 0;

    if (bust.current) {
      const breath = 1 + Math.sin(elapsed * 1.45) * 0.008;
      bust.current.scale.set(breath, breath, breath);
      bust.current.position.y = Math.sin(elapsed * 1.45) * 0.008 - 0.16;
    }
    if (head.current) {
      head.current.rotation.y = idleSway + (thinking ? 0.035 : 0);
      head.current.rotation.z = current.headTilt + thinkingTilt;
      head.current.rotation.x = current.headNod + thinkingNod;
    }

    const eyeScale = Math.max(0.04, current.eyeOpenness * blink);
    eyes.current.forEach((eye) => eye?.scale.set(1, eyeScale, 1));

    const gazeX = thinking
      ? Math.sin(elapsed * 1.9) * 0.035
      : Math.sin(elapsed * 0.42) * 0.012;
    const gazeY = thinking ? Math.cos(elapsed * 1.25) * 0.018 : 0;
    pupils.current.forEach((pupil) => {
      if (!pupil) return;
      pupil.position.x = gazeX;
      pupil.position.y = gazeY;
    });

    const browY = 0.48 + current.browLift * 0.15;
    if (leftBrow.current) {
      leftBrow.current.position.y = browY;
      leftBrow.current.rotation.z = -0.08 - current.browSlant * 0.42;
    }
    if (rightBrow.current) {
      rightBrow.current.position.y = browY;
      rightBrow.current.rotation.z = 0.08 + current.browSlant * 0.42;
    }

    const speechOpen = speaking
      ? 0.16 + Math.abs(Math.sin(elapsed * 7.5)) * 0.36
      : 0;
    const openAmount = Math.max(current.mouthOpen, speechOpen);
    const mouthHalfWidth = MathUtils.lerp(0.13, 0.23, current.mouthWidth);
    const mouthOpenHeight = 0.006 + openAmount * 0.12;
    const mouthCenterY = -0.4;
    const mouthPoint = (index: number, lip: -1 | 1) => {
      const u = (index / (MOUTH_SEGMENT_COUNT - 1)) * 2 - 1;
      const x = u * mouthHalfWidth;
      const curveY = current.mouthCurve * 0.072 * u * u;
      const openingY =
        lip * mouthOpenHeight * Math.sqrt(Math.max(0, 1 - u * u));
      return { x, y: mouthCenterY + curveY + openingY };
    };

    if (mouthOpening.current) {
      mouthOpening.current.position.y = mouthCenterY;
      mouthOpening.current.scale.y = mouthOpenHeight * 0.92;
      mouthOpening.current.scale.x =
        mouthHalfWidth * MathUtils.lerp(0.72, 0.92, openAmount);
    }

    const positionLip = (segments: Array<Mesh | null>, lip: -1 | 1) => {
      segments.forEach((segment, index) => {
        if (!segment) return;
        const point = mouthPoint(index, lip);
        const previous = mouthPoint(Math.max(0, index - 1), lip);
        const next = mouthPoint(
          Math.min(MOUTH_SEGMENT_COUNT - 1, index + 1),
          lip,
        );
        segment.position.set(point.x, point.y, 1.026 + lip * 0.002);
        segment.rotation.z = Math.atan2(
          next.y - previous.y,
          next.x - previous.x,
        );
        const segmentScale =
          (((mouthHalfWidth * 2) / (MOUTH_SEGMENT_COUNT - 1)) / 0.04) *
          1.6;
        const isEndpoint =
          index === 0 || index === MOUTH_SEGMENT_COUNT - 1;
        segment.scale.x = segmentScale * (isEndpoint ? 0.55 : 1);
      });
    };

    positionLip(upperLip.current, 1);
    positionLip(lowerLip.current, -1);
  });

  return (
    <>
      <group ref={bust} position={[0, -0.16, 0]}>
        <RoundedBox
          args={[2.35, 1.18, 0.9]}
          radius={0.34}
          smoothness={5}
          position={[0, -1.48, -0.15]}
          scale={[1, 0.82, 1]}
        >
          <meshStandardMaterial color={SHIRT} roughness={0.72} />
        </RoundedBox>

        <mesh position={[0, -0.94, -0.02]}>
          <cylinderGeometry args={[0.34, 0.42, 0.74, 20]} />
          <meshStandardMaterial color={SKIN} roughness={0.76} />
        </mesh>

        <group ref={head}>
          <mesh scale={[1.02, 1.18, 0.92]}>
            <sphereGeometry args={[1, 40, 32]} />
            <meshStandardMaterial color={SKIN_LIGHT} roughness={0.78} />
          </mesh>

          <mesh position={[0, 0.83, -0.08]} scale={[1.01, 0.55, 0.94]}>
            <sphereGeometry args={[1, 32, 20, 0, Math.PI * 2, 0, 1.65]} />
            <meshStandardMaterial color={HAIR} roughness={0.88} />
          </mesh>
          <mesh
            position={[-0.67, 0.56, 0.5]}
            rotation={[0.1, -0.18, -0.45]}
            scale={[0.24, 0.5, 0.18]}
          >
            <sphereGeometry args={[1, 20, 16]} />
            <meshStandardMaterial color={HAIR} roughness={0.88} />
          </mesh>
          <mesh
            position={[0.67, 0.56, 0.5]}
            rotation={[0.1, 0.18, 0.45]}
            scale={[0.24, 0.5, 0.18]}
          >
            <sphereGeometry args={[1, 20, 16]} />
            <meshStandardMaterial color={HAIR} roughness={0.88} />
          </mesh>

          {[-1, 1].map((side) => (
            <mesh
              key={side}
              position={[side * 0.98, 0.02, -0.03]}
              scale={[0.15, 0.27, 0.12]}
            >
              <sphereGeometry args={[1, 20, 16]} />
              <meshStandardMaterial color={SKIN} roughness={0.82} />
            </mesh>
          ))}

          {EYE_OFFSETS.map((side, index) => (
            <group
              key={side}
              ref={(eye) => {
                eyes.current[index] = eye;
              }}
              position={[side * 0.39, 0.2, 0.84]}
            >
              <mesh scale={[1, 0.64, 0.46]}>
                <sphereGeometry args={[0.21, 24, 18]} />
                <meshStandardMaterial
                  color={EYE}
                  emissive="#e5f4e8"
                  emissiveIntensity={0.08}
                  roughness={0.3}
                />
              </mesh>
              <mesh
                ref={(pupil) => {
                  pupils.current[index] = pupil;
                }}
                position={[0, 0, 0.095]}
              >
                <sphereGeometry args={[0.082, 20, 14]} />
                <meshStandardMaterial color={IRIS} roughness={0.3} />
                <mesh position={[0, 0, 0.073]}>
                  <sphereGeometry args={[0.038, 16, 12]} />
                  <meshStandardMaterial color={PUPIL} roughness={0.24} />
                </mesh>
                <mesh position={[-0.025, 0.03, 0.105]}>
                  <sphereGeometry args={[0.014, 12, 10]} />
                  <meshStandardMaterial
                    color="#ffffff"
                    emissive="#ffffff"
                    emissiveIntensity={0.35}
                    roughness={0.16}
                  />
                </mesh>
              </mesh>
            </group>
          ))}

          <mesh
            ref={leftBrow}
            position={[-0.39, 0.48, 0.88]}
            rotation={[0, 0, -0.08]}
          >
            <boxGeometry args={[0.4, 0.065, 0.055]} />
            <meshStandardMaterial color={HAIR} roughness={0.86} />
          </mesh>
          <mesh
            ref={rightBrow}
            position={[0.39, 0.48, 0.88]}
            rotation={[0, 0, 0.08]}
          >
            <boxGeometry args={[0.4, 0.065, 0.055]} />
            <meshStandardMaterial color={HAIR} roughness={0.86} />
          </mesh>

          <mesh position={[0, -0.08, 0.93]} scale={[0.16, 0.27, 0.2]}>
            <sphereGeometry args={[1, 20, 16]} />
            <meshStandardMaterial color={SKIN} roughness={0.8} />
          </mesh>

          <mesh
            ref={mouthOpening}
            position={[0, -0.41, 1.005]}
            scale={[0.15, 0.02, 0.035]}
          >
            <sphereGeometry args={[1, 24, 18]} />
            <meshStandardMaterial color="#35131c" roughness={0.56} />
          </mesh>
          {MOUTH_SEGMENT_INDICES.map((index) => (
            <mesh
              key={`upper-${index}`}
              ref={(segment) => {
                upperLip.current[index] = segment;
              }}
              scale={[1, 0.4, 0.42]}
            >
              <sphereGeometry args={[0.04, 14, 10]} />
              <meshStandardMaterial
                color={MOUTH_LIGHT}
                roughness={0.46}
              />
            </mesh>
          ))}
          {MOUTH_INNER_SEGMENT_INDICES.map((index) => (
            <mesh
              key={`lower-${index}`}
              ref={(segment) => {
                lowerLip.current[index] = segment;
              }}
              scale={[1, 0.4, 0.42]}
            >
              <sphereGeometry args={[0.04, 14, 10]} />
              <meshStandardMaterial color={MOUTH} roughness={0.56} />
            </mesh>
          ))}
        </group>
      </group>

      <ContactShadows
        position={[0, -1.72, 0]}
        opacity={0.25}
        scale={4.5}
        blur={2.5}
        far={3.5}
      />
    </>
  );
}
