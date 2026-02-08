let audioCtx: AudioContext | null = null;

export function playBeep(frequency = 880, durationMs = 120): void {
  if (typeof window === "undefined") {
    return;
  }
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  const oscillator = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = frequency;
  gain.gain.value = 0.04;
  oscillator.connect(gain);
  gain.connect(audioCtx.destination);
  oscillator.start();
  oscillator.stop(audioCtx.currentTime + durationMs / 1000);
}

