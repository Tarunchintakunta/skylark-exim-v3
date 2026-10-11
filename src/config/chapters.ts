import { film, type CaptionCopy } from './content'

/**
 * Visual source of one segment. A chapter's scroll length is split evenly across its segments, unless a still sets `span`.
 * - video: public/media/<id>_{960,1280,1920}.mp4 + <id>_{960,1280,1920}.webp first-frame posters + <id>_end_1920.webp
 * - still: a clip's first frame (every clip tier), or a ph-* stand-in at 720 / 1280, until the scene's clip lands (no label is ever shown; open stand-ins are listed in PR bodies)
 * - gradient: deep-blue stand-in
 * - dom: documentation interlude over a pre-blurred still
 * - globe: the R3F globe
 */
export type Media =
  | { kind: 'video'; id: string; alt: string }
  | { kind: 'still'; poster: string; alt: string; /** share of the chapter's scroll, 0–1 (e.g. to end with its caption) */ span?: number }
  | { kind: 'gradient'; alt: string }
  | { kind: 'dom'; poster: string; alt: string }
  | { kind: 'globe'; alt: string }

export type Join = 'shared-frame' | 'crossfade' | 'cut'

export interface Caption extends CaptionCopy {
  at: [number, number]
  /** DOM extra shown with the caption */
  extra?: 'label-card' | 'doc-cards' | 'markets'
}

export interface ChapterDef {
  id: string
  path: 'ocean' | 'pond' | 'shared'
  /** accessible chapter name */
  label: string
  /** desktop scroll length in vh (mobile uses 0.8×) */
  vh: number
  media: Media[]
  captions: Caption[]
  /** how this chapter hands off to the next one */
  joinNext: Join
  /** copy colour scheme; the globe opens into daylight */
  theme?: 'light'
  /** 'soft': a light, neutral bottom scrim instead of the deep-sea one, for daylight footage (the port) */
  scrim?: 'soft'
}

const caps = (id: string, ranges: [number, number][]): Caption[] => film[id].map((c, i) => ({ ...c, at: ranges[i] }))

const start: ChapterDef = {
  id: 'start', path: 'shared', label: 'Start', vh: 120, joinNext: 'shared-frame',
  media: [{ kind: 'video', id: 'opening', alt: 'Underwater light rising to the surface of the sea at dusk.' }],
  captions: [],
}

const OCEAN_ONLY: ChapterDef[] = [
  {
    id: 'o1', path: 'ocean', label: 'Setting out', vh: 200, joinNext: 'shared-frame',
    media: [
      { kind: 'video', id: 'a1', alt: 'A harbour at sunrise; crew load ice onto a fishing boat.' },
      { kind: 'video', id: 'a2', alt: 'The fishing boat steams out to open sea.' },
    ],
    captions: caps('o1', [[0.08, 0.92]]),
  },
  {
    id: 'o2', path: 'ocean', label: 'The catch', vh: 140, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'a3', alt: 'Yellowfin tuna on crushed ice in the boat’s hold.' }],
    captions: caps('o2', [[0.55, 1]]),
  },
  {
    id: 'o3', path: 'ocean', label: 'On ice', vh: 100, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'a3', alt: 'Looking down into the ice hold: yellowfin tuna on crushed ice.' }],
    captions: caps('o3', [[0.1, 0.95]]),
  },
  {
    id: 'o4', path: 'ocean', label: 'Back to Vizag', vh: 160, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'a4', alt: 'Crates go into a refrigerated truck, which drives the coast road and reverses to the lit intake door.' }],
    captions: caps('o4', [[0.1, 0.9]]),
  },
]

const POND_ONLY: ChapterDef[] = [
  {
    id: 'p1', path: 'pond', label: 'The ponds', vh: 120, joinNext: 'crossfade',
    media: [{ kind: 'still', poster: 'b2', alt: 'Aerial view of a grid of shrimp ponds with aerators at dusk.' }],
    captions: caps('p1', [[0.1, 0.92]]),
  },
  {
    id: 'p2', path: 'pond', label: 'Traceable', vh: 100, joinNext: 'shared-frame',
    media: [{ kind: 'video', id: 'b2', alt: 'A gloved hand takes a pond water sample; the meter reading goes into a logbook.' }],
    captions: caps('p2', [[0.1, 0.92]]),
  },
  {
    id: 'p3', path: 'pond', label: 'Harvest', vh: 120, joinNext: 'crossfade',
    media: [
      { kind: 'video', id: 'hf-harvest', alt: 'Sunrise at a shrimp pond: workers wade waist-deep drawing the drag net toward the bank.' },
      { kind: 'video', id: 'hf-sort', alt: 'On the pond bank, workers tip live shrimp onto crushed ice in blue and white crates beside the refrigerated truck.' },
    ],
    captions: caps('p3', [[0.1, 0.9]]),
  },
]

const SHARED: ChapterDef[] = [
  {
    id: 'intake', path: 'shared', label: 'Intake', vh: 120, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'ph-p-intake', alt: 'A refrigerated truck backed up to the lit intake door of the plant at night.' }],
    captions: caps('intake', [[0.1, 0.92]]),
  },
  {
    id: 'process', path: 'shared', label: 'Process', vh: 200, joinNext: 'shared-frame',
    media: [{ kind: 'still', poster: 'ph-p-proc', alt: 'A clean quality lab bench with a microscope and a test instrument.' }],
    captions: caps('process', [[0.02, 0.33], [0.33, 0.66], [0.66, 0.98]]),
  },
  {
    id: 'coldchain', path: 'shared', label: 'Lab · freeze · pack', vh: 240, joinNext: 'shared-frame',
    // the lab still holds "Tested before it moves." (0–20%), the cold store the freezing / packing / cold-storage captions
    media: [
      { kind: 'still', poster: 'ph-p-lab', span: 0.2, alt: 'A clean quality lab bench with a microscope and a test instrument.' },
      { kind: 'still', poster: 'ph-p-freeze', alt: 'A cold-store aisle with racks of white cartons on pallets.' },
    ],
    captions: caps('coldchain', [[0.02, 0.2], [0.2, 0.55], [0.55, 0.8], [0.8, 1]]).map((c, i) => (i === 2 ? { ...c, extra: 'label-card' as const } : c)),
  },
  {
    id: 'docs', path: 'shared', label: 'Documentation', vh: 100, joinNext: 'cut',
    media: [{ kind: 'dom', poster: 'ph-p-freeze', alt: 'Three cards: export documents, compliance, shipment tracking.' }],
    captions: caps('docs', [[0.05, 0.95]]).map((c) => ({ ...c, extra: 'doc-cards' as const })),
  },
  {
    id: 'port', path: 'shared', label: 'The port', vh: 140, joinNext: 'shared-frame', scrim: 'soft',
    media: [{ kind: 'video', id: 'x-cranes', alt: 'A white refrigerated truck parks under a ship-to-shore crane, which lifts the white reefer container on its cables onto the container ship.' }],
    captions: caps('port', [[0.1, 0.92]]),
  },
  {
    id: 'sea', path: 'shared', label: 'At sea', vh: 120, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'x-ship', alt: 'Seen from straight above, the loaded container ship sails out across deep blue water, trailing a white wake.' }],
    captions: caps('sea', [[0.1, 0.85]]),
  },
  {
    id: 'world', path: 'shared', label: 'The world', vh: 220, joinNext: 'cut', theme: 'light',
    media: [{ kind: 'globe', alt: 'A bright daytime globe with gold routes from Visakhapatnam to 16 markets.' }],
    captions: caps('world', [[0.3, 1.01]]).map((c) => ({ ...c, body: undefined, extra: 'markets' as const })),
  },
]

export const OCEAN: ChapterDef[] = [start, ...OCEAN_ONLY, ...SHARED]
export const POND: ChapterDef[] = [start, ...POND_ONLY, ...SHARED]
export const chaptersFor = (path: 'ocean' | 'pond') => (path === 'pond' ? POND : OCEAN)
