// Device/mode flags, read once at startup. A reload picks up changes (good enough for a marketing site).
const mq = (q: string) => typeof matchMedia !== 'undefined' && matchMedia(q).matches
const conn = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection

export const env = {
  reduced: mq('(prefers-reduced-motion: reduce)'),
  coarse: mq('(pointer: coarse)'),
  /** < 820 px or touch: 720w clips, native scroll, 0.8× chapter lengths, simplified 3D */
  mobile: mq('(max-width: 819px)') || mq('(pointer: coarse)'),
  saveData: Boolean(conn?.saveData),
  fine: mq('(hover: hover) and (pointer: fine)'),
}
