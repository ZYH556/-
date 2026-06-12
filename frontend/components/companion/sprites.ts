export type PetMood =
  | "idle"
  | "walk"
  | "stumble"
  | "happy"
  | "celebrate"
  | "sleep"
  | "think"
  | "work"
  | "study";

export interface PetSheet {
  src: string;
  cols: number;
  rows: number;
  frameWidth: number;
  frameHeight: number;
}

export interface PetMoodSpec {
  row: number;
  frames: number;
  fps: number;
}

export const PET_SHEET: PetSheet = {
  src: "/pets/cow/spritesheet.webp",
  cols: 8,
  rows: 9,
  frameWidth: 192,
  frameHeight: 208,
};

export const PET_MOODS: Record<PetMood, PetMoodSpec> = {
  idle: { row: 0, frames: 8, fps: 5 },
  walk: { row: 1, frames: 8, fps: 7 },
  stumble: { row: 2, frames: 8, fps: 6 },
  happy: { row: 3, frames: 8, fps: 7 },
  celebrate: { row: 4, frames: 8, fps: 7 },
  sleep: { row: 5, frames: 8, fps: 3 },
  think: { row: 6, frames: 8, fps: 5 },
  work: { row: 7, frames: 8, fps: 6 },
  study: { row: 8, frames: 8, fps: 5 },
};

/** 学伴在无交互这么久后进入睡觉状态（毫秒）。 */
export const PET_SLEEP_AFTER_MS = 120_000;
