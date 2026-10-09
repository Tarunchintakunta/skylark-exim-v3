import { film, type CaptionCopy } from './content'
import { COLD_STORE_TEMP, type HudState } from './hud'

/**
 * Visual source of one segment. A chapter's scroll length is split evenly across its segments.
 * - video: public/media/<id>_{1280,720}.mp4 + <id>_{1280,720}.webp first-frame posters + <id>_end_1280.webp
 * - still: placeholder image (CLAUDE_PROMPT §6) with a slow 1.04 scale on scroll until the real clip lands
 * - gradient: deep-blue placeholder for x-cranes / x-ship
 * - dom: documentation interlude over a blurred, darkened still
 * - globe: the R3F globe
 */
export type Media =
  | { kind: 'video'; id: string; alt: string }
  | { kind: 'still'; poster: string; alt: string; awaiting: string }
  | { kind: 'gradient'; alt: string; awaiting: string }
  | { kind: 'dom'; poster: string; alt: string }
  | { kind: 'globe'; alt: string }

export type Join = 'shared-frame' | 'crossfade' | 'cut'

export interface Caption extends CaptionCopy {
  at: [number, number]
  /** DOM extra shown with the caption */
  extra?: 'label-card' | 'doc-cards'
}

export interface ChapterDef {
  id: string
  path: 'ocean' | 'pond' | 'shared'
  /** rail / nav label */
  label: string
  /** desktop scroll length in vh (mobile uses 0.8×) */
  vh: number
  media: Media[]
  captions: Caption[]
  hud: HudState[]
  /** how this chapter hands off to the next one */
  joinNext: Join
}

const caps = (id: string, ranges: [number, number][]): Caption[] => film[id].map((c, i) => ({ ...c, at: ranges[i] }))

const start: ChapterDef = {
  id: 'start', path: 'shared', label: 'Start', vh: 120, joinNext: 'shared-frame',
  media: [{ kind: 'video', id: 'opening', alt: 'Underwater light rising to the surface of the sea at dusk.' }],
  captions: [],
  hud: [{ at: 0, step: '01', name: 'Raw material procurement', state: 'Origin' }],
}

const OCEAN_ONLY: ChapterDef[] = [
  {
    id: 'o1', path: 'ocean', label: 'Setting out', vh: 200, joinNext: 'shared-frame',
    media: [
      { kind: 'video', id: 'a1', alt: 'A harbour at sunrise; crew load ice onto a fishing boat.' },
      { kind: 'video', id: 'a2', alt: 'The fishing boat steams out to open sea.' },
    ],
    captions: caps('o1', [[0.08, 0.92]]),
    hud: [{ at: 0, step: '01', name: 'Procurement', state: 'At sea' }],
  },
  {
    id: 'o2', path: 'ocean', label: 'The catch', vh: 140, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'a3', awaiting: 'o-catch', alt: 'Yellowfin tuna on crushed ice in the boat’s hold.' }],
    captions: caps('o2', [[0.55, 1]]),
    hud: [{ at: 0, step: '01', name: 'Procurement', state: 'On deck' }],
  },
  {
    id: 'o3', path: 'ocean', label: 'On ice', vh: 100, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'a3', alt: 'Looking down into the ice hold: yellowfin tuna on crushed ice.' }],
    captions: caps('o3', [[0.1, 0.95]]),
    hud: [{ at: 0, step: '01', name: 'Procurement', state: 'Chilled' }],
  },
  {
    id: 'o4', path: 'ocean', label: 'Back to Vizag', vh: 160, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'a4', alt: 'Crates go into a refrigerated truck, which drives the coast road and reverses to the lit intake door.' }],
    captions: caps('o4', [[0.1, 0.9]]),
    hud: [{ at: 0, step: '02', name: 'Receiving & washing', state: 'In transit · chilled' }],
  },
]

const POND_ONLY: ChapterDef[] = [
  {
    id: 'p1', path: 'pond', label: 'The ponds', vh: 120, joinNext: 'crossfade',
    media: [{ kind: 'still', poster: 'b2', awaiting: 'p-ponds', alt: 'Aerial view of a grid of shrimp ponds with aerators at dusk.' }],
    captions: caps('p1', [[0.1, 0.92]]),
    hud: [{ at: 0, step: '01', name: 'Procurement', state: 'Origin · farm' }],
  },
  {
    id: 'p2', path: 'pond', label: 'Traceable', vh: 100, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'b2', alt: 'A gloved hand takes a pond water sample; the meter reading goes into a logbook.' }],
    captions: caps('p2', [[0.1, 0.92]]),
    hud: [{ at: 0, step: '01', name: 'Procurement', state: 'Quality check at source' }],
  },
  {
    id: 'p3', path: 'pond', label: 'Harvest', vh: 120, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'b3', alt: 'Shrimp go into iced crates, onto a small refrigerated truck that reverses to the plant bay.' }],
    captions: caps('p3', [[0.1, 0.9]]),
    hud: [{ at: 0, step: '02', name: 'Receiving & washing', state: 'In transit · chilled' }],
  },
]

const SHARED: ChapterDef[] = [
  {
    id: 'intake', path: 'shared', label: 'Intake', vh: 120, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'ph-p-intake', awaiting: 'p-intake', alt: 'A refrigerated truck backed up to the lit intake door of the plant at night.' }],
    captions: caps('intake', [[0.1, 0.92]]),
    hud: [{ at: 0, step: '02', name: 'Receiving & washing', state: 'Received' }],
  },
  {
    id: 'process', path: 'shared', label: 'Process', vh: 200, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'ph-p-proc', awaiting: 'p-proc', alt: 'A clean quality lab bench with a microscope and a test instrument.' }],
    captions: caps('process', [[0.02, 0.33], [0.33, 0.66], [0.66, 0.98]]),
    hud: [
      { at: 0, step: '02', name: 'Washing' },
      { at: 0.33, step: '04', name: 'Grading & sorting' },
      { at: 0.66, step: '03', name: 'Processing' },
    ],
  },
  {
    id: 'coldchain', path: 'shared', label: 'Lab · freeze · pack', vh: 240, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'ph-p-freeze', awaiting: 'p-freeze', alt: 'A cold-store aisle with racks of white cartons on pallets.' }],
    captions: caps('coldchain', [[0.02, 0.2], [0.2, 0.55], [0.55, 0.8], [0.8, 1]]).map((c, i) => (i === 2 ? { ...c, extra: 'label-card' as const } : c)),
    hud: [
      { at: 0, step: '05', name: 'Quality control' },
      { at: 0.2, step: '06', name: 'Freezing & glazing' },
      { at: 0.55, step: '07', name: 'Packaging' },
      { at: 0.8, step: '08', name: 'Cold storage', temp: COLD_STORE_TEMP },
    ],
  },
  {
    id: 'docs', path: 'shared', label: 'Documentation', vh: 100, joinNext: 'cut',
    media: [{ kind: 'dom', poster: 'ph-p-freeze', alt: 'Three cards: export documents, compliance, shipment tracking.' }],
    captions: caps('docs', [[0.05, 0.95]]),
    hud: [{ at: 0, step: '09', name: 'Export documentation & logistics', state: 'Documented' }],
  },
  {
    id: 'port', path: 'shared', label: 'The port', vh: 140, joinNext: 'shared-frame',
    media: [{ kind: 'gradient', awaiting: 'x-cranes', alt: 'Deep blue placeholder for the container port.' }],
    captions: caps('port', [[0.1, 0.92]]),
    hud: [{ at: 0, step: '09', name: 'Export', state: 'Reefer container' }],
  },
  {
    id: 'sea', path: 'shared', label: 'At sea', vh: 120, joinNext: 'crossfade',
    media: [{ kind: 'gradient', awaiting: 'x-ship', alt: 'Deep blue placeholder for the container ship at sea.' }],
    captions: caps('sea', [[0.1, 0.85]]),
    hud: [{ at: 0, step: '09', name: 'Export', state: 'At sea · cold chain' }],
  },
  {
    id: 'world', path: 'shared', label: 'The world', vh: 220, joinNext: 'cut',
    media: [{ kind: 'globe', alt: 'A bright daytime globe with gold routes from Visakhapatnam to 16 markets.' }],
    captions: caps('world', [[0.05, 1]]),
    hud: [{ at: 0, step: '09', name: 'Export', state: '16 markets' }],
  },
]

export const OCEAN: ChapterDef[] = [start, ...OCEAN_ONLY, ...SHARED]
export const POND: ChapterDef[] = [start, ...POND_ONLY, ...SHARED]
export const chaptersFor = (path: 'ocean' | 'pond') => (path === 'pond' ? POND : OCEAN)
