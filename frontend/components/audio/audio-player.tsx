"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

/** Interactive waveform player backed by wavesurfer.js. `src` is a full URL. */
export function AudioPlayer({ src }: { src: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<{ playPause: () => void; destroy: () => void } | null>(null);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    let disposed = false;
    setReady(false);
    setPlaying(false);

    (async () => {
      const WaveSurfer = (await import("wavesurfer.js")).default;
      if (disposed || !containerRef.current) return;

      const styles = getComputedStyle(document.documentElement);
      const primary = styles.getPropertyValue("--primary").trim() || "#0d6e63";
      const muted = styles.getPropertyValue("--muted-foreground").trim() || "#5c6b67";

      const ws = WaveSurfer.create({
        container: containerRef.current,
        url: src,
        height: 64,
        waveColor: muted,
        progressColor: primary,
        cursorColor: primary,
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
      });
      wsRef.current = ws;
      ws.on("ready", () => setReady(true));
      ws.on("play", () => setPlaying(true));
      ws.on("pause", () => setPlaying(false));
      ws.on("finish", () => setPlaying(false));
    })();

    return () => {
      disposed = true;
      wsRef.current?.destroy();
      wsRef.current = null;
    };
  }, [src]);

  return (
    <div className="flex items-center gap-3">
      <Button
        size="icon"
        aria-label={playing ? "Pause" : "Play"}
        disabled={!ready}
        onClick={() => wsRef.current?.playPause()}
      >
        {playing ? <Pause /> : <Play />}
      </Button>
      <div ref={containerRef} className="flex-1 min-w-0" />
    </div>
  );
}
