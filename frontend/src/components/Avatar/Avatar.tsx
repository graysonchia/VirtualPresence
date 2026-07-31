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
const MOUTH = "#6e2d32";

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
}

export function Avatar({ conversationState, emotion }: AvatarProps) {
  const bust = useRef<Group>(null);
  const head = useRef<Group>(null);
  const leftEye = useRef<Group>(null);
  const rightEye = useRef<Group>(null);
  const leftPupil = useRef<Mesh>(null);
  const rightPupil = useRef<Mesh>(null);
  const leftBrow = useRef<Mesh>(null);
  const rightBrow = useRef<Mesh>(null);
  const mouthOpening = useRef<Mesh>(null);
  const mouthLeft = useRef<Mesh>(null);
  const mouthRight = useRef<Mesh>(null);
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
    const idleSway = Math.sin(elapsed * 0.62) * 0.025;
    const thinkingTilt = thinking ? Math.sin(elapsed * 1.15) * 0.035 + 0.07 : 0;
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
    leftEye.current?.scale.set(1, eyeScale, 1);
    rightEye.current?.scale.set(1, eyeScale, 1);

    const gazeX = thinking
      ? Math.sin(elapsed * 1.9) * 0.035
      : Math.sin(elapsed * 0.42) * 0.012;
    const gazeY = thinking ? Math.cos(elapsed * 1.25) * 0.018 : 0;
    if (leftPupil.current) {
      leftPupil.current.position.x = gazeX;
      leftPupil.current.position.y = gazeY;
    }
    if (rightPupil.current) {
      rightPupil.current.position.x = gazeX;
      rightPupil.current.position.y = gazeY;
    }

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
    if (mouthOpening.current) {
      mouthOpening.current.scale.y = 0.028 + openAmount * 0.12;
      mouthOpening.current.scale.x = 0.15 - openAmount * 0.018;
    }

    const mouthAngle = current.mouthCurve * 0.38;
    if (mouthLeft.current) {
      mouthLeft.current.rotation.z = -mouthAngle;
      mouthLeft.current.position.y = -0.37 - current.mouthCurve * 0.022;
    }
    if (mouthRight.current) {
      mouthRight.current.rotation.z = mouthAngle;
      mouthRight.current.position.y = -0.37 - current.mouthCurve * 0.022;
    }
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

          <group ref={leftEye} position={[-0.39, 0.2, 0.84]}>
            <mesh scale={[1, 0.64, 0.46]}>
              <sphereGeometry args={[0.21, 24, 18]} />
              <meshStandardMaterial color={EYE} roughness={0.38} />
            </mesh>
            <mesh ref={leftPupil} position={[0, 0, 0.095]}>
              <sphereGeometry args={[0.082, 20, 14]} />
              <meshStandardMaterial color={IRIS} roughness={0.4} />
            </mesh>
          </group>
          <group ref={rightEye} position={[0.39, 0.2, 0.84]}>
            <mesh scale={[1, 0.64, 0.46]}>
              <sphereGeometry args={[0.21, 24, 18]} />
              <meshStandardMaterial color={EYE} roughness={0.38} />
            </mesh>
            <mesh ref={rightPupil} position={[0, 0, 0.095]}>
              <sphereGeometry args={[0.082, 20, 14]} />
              <meshStandardMaterial color={IRIS} roughness={0.4} />
            </mesh>
          </group>

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
            scale={[0.15, 0.028, 0.035]}
          >
            <sphereGeometry args={[1, 24, 18]} />
            <meshStandardMaterial color="#3c1720" roughness={0.7} />
          </mesh>
          <mesh
            ref={mouthLeft}
            position={[-0.09, -0.37, 1.025]}
            rotation={[0, 0, -0.03]}
          >
            <boxGeometry args={[0.19, 0.042, 0.03]} />
            <meshStandardMaterial color={MOUTH} roughness={0.68} />
          </mesh>
          <mesh
            ref={mouthRight}
            position={[0.09, -0.37, 1.025]}
            rotation={[0, 0, 0.03]}
          >
            <boxGeometry args={[0.19, 0.042, 0.03]} />
            <meshStandardMaterial color={MOUTH} roughness={0.68} />
          </mesh>
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
