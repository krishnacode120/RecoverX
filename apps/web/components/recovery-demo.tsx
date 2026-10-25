"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import {
  Check,
  FileImage,
  HardDrive,
  Pause,
  Play,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import styles from "@/app/home.module.css";

const phases = [
  {
    title: "Looking beneath the surface",
    label: "Read surviving blocks",
    status: "Reading source",
    detail: "A read-only scan finds surviving data.",
  },
  {
    title: "A fragment becomes a possibility",
    label: "Inspect the evidence",
    status: "Candidate found",
    detail: "Review a candidate before choosing to export.",
  },
  {
    title: "Recovered. Then checked.",
    label: "Verify the export",
    status: "Export verified",
    detail: "Compare the output with the scanned bytes.",
  },
];

export function RecoveryDemo() {
  const [phase, setPhase] = useState(0);
  const [playing, setPlaying] = useState(true);
  const reducedMotion = useReducedMotion();
  const running = playing && !reducedMotion;
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(
      () => setPhase((value) => (value + 1) % phases.length),
      4200,
    );
    return () => window.clearInterval(timer);
  }, [running]);

  return (
    <div
      className={`${styles.demo} ${!running ? styles.paused : ""}`}
      data-phase={phase}
    >
      <div className={styles.demoTop}>
        <span>
          <span className={styles.demoDot} /> RECOVERY IN MOTION
        </span>
        <span>ILLUSTRATIVE DEMO</span>
      </div>
      <div className={styles.scanScene} aria-hidden="true">
        <div className={styles.sceneGrid} />
        <div className={styles.disk}>
          <div className={styles.diskRing} />
          <div className={styles.diskRingInner} />
          <div className={styles.sweep} />
          <div className={styles.diskHub}>
            <HardDrive size={35} strokeWidth={1.2} />
            <span>READ ONLY</span>
          </div>
          <span className={`${styles.sector} ${styles.sectorOne}`} />
          <span className={`${styles.sector} ${styles.sectorTwo}`} />
          <span className={`${styles.sector} ${styles.sectorThree}`} />
        </div>
        <div className={styles.sourceBadge}>
          <HardDrive size={14} />
          <span>sample-disk.img</span>
          <span>LOCAL</span>
        </div>
        <div className={styles.fileCard}>
          <span className={styles.fileIcon}>
            <FileImage size={24} strokeWidth={1.5} />
          </span>
          <div>
            <strong>memories.jpg</strong>
            <small>
              {phase === 0
                ? "Looking for file content"
                : phase === 1
                  ? "Available for inspection"
                  : "Output matches scanned bytes"}
            </small>
          </div>
          <span className={styles.fileCheck}>
            {phase === 2 ? <Check size={16} /> : <ScanLine size={16} />}
          </span>
        </div>
        <div className={styles.sectorMap}>
          {Array.from({ length: 48 }, (_, i) => (
            <i
              key={i}
              className={(i * 7) % 11 < phase * 3 + 2 ? styles.foundBlock : ""}
            />
          ))}
        </div>
      </div>
      <div className={styles.demoDescription}>
        <div>
          <span className={styles.demoStatus}>
            {phase === 2 ? <ShieldCheck size={13} /> : <ScanLine size={13} />}
            {phases[phase].status}
          </span>
          <h2>{phases[phase].title}</h2>
          <p>{phases[phase].detail}</p>
        </div>
        <button
          type="button"
          className={styles.playControl}
          aria-label={running ? "Pause animation" : "Play animation"}
          disabled={!!reducedMotion}
          title={
            reducedMotion
              ? "Animation disabled by your reduced-motion preference"
              : undefined
          }
          onClick={() => setPlaying(!playing)}
        >
          {running ? <Pause size={15} /> : <Play size={15} />}
        </button>
      </div>
      <div
        className={styles.demoSteps}
        aria-label="Recovery illustration steps"
      >
        {phases.map((item, index) => (
          <button
            type="button"
            key={item.label}
            aria-pressed={phase === index}
            onClick={() => {
              setPhase(index);
              setPlaying(false);
            }}
          >
            <span>0{index + 1}</span>
            {item.label}
            <i />
          </button>
        ))}
      </div>
      <p className={styles.demoNote}>
        A sample sequence. No files or drives are accessed.
      </p>
    </div>
  );
}
