"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Plays a specific [start, end] window of an audio file — the "Listen" action
 * in the Listen & Label workflow. A single shared HTMLAudioElement plays the
 * exact detection window and stops at its end.
 */
export function useSegmentPlayer(src: string) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const stopAtRef = useRef<number>(0);
  const [playingKey, setPlayingKey] = useState<string | null>(null);

  useEffect(() => {
    const audio = new Audio(src);
    audio.preload = "none";
    audioRef.current = audio;

    const onTime = () => {
      if (audio.currentTime >= stopAtRef.current) {
        audio.pause();
        setPlayingKey(null);
      }
    };
    const onEnded = () => setPlayingKey(null);
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnded);
    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("ended", onEnded);
    };
  }, [src]);

  const play = useCallback((key: string, start: number, end: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playingKey === key) {
      audio.pause();
      setPlayingKey(null);
      return;
    }
    stopAtRef.current = end;
    audio.currentTime = start;
    void audio.play();
    setPlayingKey(key);
  }, [playingKey]);

  return { play, playingKey };
}
