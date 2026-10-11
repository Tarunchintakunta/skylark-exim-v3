import { bridge, film, type CaptionCopy } from './content'
import { MARKET_COUNT } from './markets'

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
  id: 'start', path: 'shared', label: 'Start', vh: 120, joinNext: 'crossfade',
  media: [{ kind: 'video', id: 'opening', alt: 'Dawn at sea off the Andhra coast: the camera glides at water level toward a fishing town under green hills.' }],
  captions: [],
}

const OCEAN_ONLY: ChapterDef[] = [
  {
    id: 'o1', path: 'ocean', label: 'Setting out', vh: 200, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'hf-depart', alt: 'A weathered white and blue fishing boat eases away from the stone quay at sunrise while the crew coil a rope and bring in a fender.' }],
    captions: caps('o1', [[0.08, 0.92]]),
  },
  {
    id: 'o2', path: 'ocean', label: 'The catch', vh: 140, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'hf-catch', alt: 'Fishermen in oilskins haul a dripping net in over the rail, silver fish caught in the mesh.' }],
    captions: caps('o2', [[0.55, 1]]),
  },
  {
    id: 'o3', path: 'ocean', label: 'On ice', vh: 100, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'hf-ice', alt: 'Seen from above, the crew kneel on the wet deck sorting tuna and silver fish into iced crates.' }],
    captions: caps('o3', [[0.1, 0.95]]),
  },
  {
    id: 'o4', path: 'ocean', label: 'Back to Vizag', vh: 160, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'hf-return', alt: 'Porters push trolleys of iced crates along the wharf as the fishing boat comes alongside.' }],
    captions: caps('o4', [[0.1, 0.9]]),
  },
]

const POND_ONLY: ChapterDef[] = [
  {
    id: 'p1', path: 'pond', label: 'The ponds', vh: 120, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'hf-ponds', alt: 'Aerial view over a grid of shrimp ponds on a bright morning, aerators throwing white water, a white refrigerated truck on a bund road.' }],
    captions: caps('p1', [[0.1, 0.92]]),
  },
  {
    id: 'p2', path: 'pond', label: 'Traceable', vh: 100, joinNext: 'crossfade',
    media: [{ kind: 'video', id: 'hf-sample', alt: 'A farm technician kneels on a plank walkway at the pond edge and fills a sample bottle with pond water.' }],
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
    id: 'intake', path: 'shared', label: 'Intake', vh: 120, joinNext: 'crossfade',
    media: [
      { kind: 'video', id: 'hf-arrive', alt: 'A white refrigerated truck reverses across the wet yard toward the plant loading dock while a worker in a hi-vis vest waves it back.' },
      { kind: 'video', id: 'hf-intake', alt: 'Inside the receiving dock, masked workers in coveralls and caps slide crates of shrimp on ice onto steel trolleys.' },
    ],
    captions: caps('intake', [[0.1, 0.92]]),
  },
  {
    id: 'process', path: 'shared', label: 'Process', vh: 200, joinNext: 'shared-frame',
    media: [
      { kind: 'video', id: 'hf-wash', alt: 'A bright processing hall mid-shift: shrimp washed under spray bars and graded along a conveyor by workers in caps, masks and gloves.' },
      { kind: 'video', id: 'hf-peel', alt: 'Workers peel and devein shrimp by hand at a stainless table, then the camera glides through the glass door toward the quality lab.' },
    ],
    captions: caps('process', [[0.02, 0.33], [0.33, 0.66], [0.66, 0.98]]),
  },
  {
    id: 'coldchain', path: 'shared', label: 'Lab · freeze · pack', vh: 240, joinNext: 'crossfade',
    // one shot per caption: lab, IQF, packing, cold store (each a quarter of the scroll)
    media: [
      { kind: 'video', id: 'hf-lab', alt: 'In the quality lab, a technician in a white coat inspects a raw shrimp with tweezers at the window bench.' },
      { kind: 'video', id: 'hf-iqf', alt: 'Individually spaced shrimp ride a stainless mesh belt into the IQF freezing tunnel through light cold vapour.' },
      { kind: 'video', id: 'hf-pack', alt: 'A packer in a white coverall places a bag of frozen shrimp into a plain brown carton and closes it.' },
      { kind: 'video', id: 'hf-store', alt: 'A worker in a blue freezer jacket walks down a cold-store aisle between racks of plain cartons.' },
    ],
    captions: caps('coldchain', [[0.02, 0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1]]).map((c, i) => (i === 2 ? { ...c, extra: 'label-card' as const } : c)),
  },
  {
    id: 'docs', path: 'shared', label: 'Documentation', vh: 100, joinNext: 'cut',
    media: [{ kind: 'dom', poster: 'ph-docs', alt: 'An export office desk in daylight: shipment folders, a binder of certificates and a laptop with a tracking map. Three cards: export documents, compliance, shipment tracking.' }],
    captions: caps('docs', [[0.05, 0.95]]).map((c) => ({ ...c, extra: 'doc-cards' as const })),
  },
  {
    id: 'port', path: 'shared', label: 'The port', vh: 140, joinNext: 'crossfade', scrim: 'soft',
    media: [
      { kind: 'video', id: 'hf-stuff', alt: 'At the plant loading bays, a forklift carries a pallet of plain cartons toward a white refrigerated trailer.' },
      { kind: 'video', id: 'hf-cranes', alt: 'On the container quay, a white reefer container on its trailer waits under a ship-to-shore crane beside the loaded ship.' },
    ],
    captions: caps('port', [[0.1, 0.92]]),
  },
  {
    id: 'sea', path: 'shared', label: 'At sea', vh: 120, joinNext: 'crossfade',
    media: [
      { kind: 'video', id: 'hf-ship', alt: 'From high on the crane, the loaded container ship pulls away from the quay behind a tug, its wake spreading.' },
      { kind: 'video', id: 'hf-sail', alt: 'Seen from high above, the loaded container ship sails out across deep blue water with a tug alongside, trailing a white wake.' },
    ],
    captions: caps('sea', [[0.1, 0.85]]),
  },
  {
    id: 'world', path: 'shared', label: 'The world', vh: 220, joinNext: 'cut', theme: 'light',
    media: [{ kind: 'globe', alt: `A bright daytime globe with gold routes from Visakhapatnam to ${MARKET_COUNT} markets.` }],
    captions: caps('world', [[0.3, 1.01]]).map((c) => ({ ...c, body: undefined, extra: 'markets' as const })),
  },
]

/** The other origin's first chapter opens with the bridge caption; its own captions start after it. */
const bridged = ([first, ...rest]: ChapterDef[]): ChapterDef[] => [
  { ...first, captions: [{ ...bridge, at: [0.02, 0.3] }, ...first.captions.map((c) => ({ ...c, at: [Math.max(c.at[0], 0.34), c.at[1]] as [number, number] }))] },
  ...rest,
]

/** One story with both origins: the chosen path first, then the other one, then the plant, port and world. */
export const OCEAN: ChapterDef[] = [start, ...OCEAN_ONLY, ...bridged(POND_ONLY), ...SHARED]
export const POND: ChapterDef[] = [start, ...POND_ONLY, ...bridged(OCEAN_ONLY), ...SHARED]
export const chaptersFor = (path: 'ocean' | 'pond') => (path === 'pond' ? POND : OCEAN)
