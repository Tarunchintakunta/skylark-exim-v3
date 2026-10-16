import type { Tier } from '../film/manifest'
import { MARKET_COORDS, MARKET_COUNT, MARKETS_BY_REGION, ORIGIN, marketLabel } from './markets'

/**
 * Story Entry (#268): the three bento cards after the homepage hero and the facts their expanded state floats in.
 * Every widget line comes from docs/CONTENT.md (`src` is its line there); no figure appears that the file does not state.
 */
export interface Widget {
  label: string
  value: string
  /** docs/CONTENT.md line */
  src: number
}

export interface EntryCard {
  id: 'wild' | 'farmed' | 'world'
  tag: string
  title: string
  cta: string
  /** expanded state */
  heading: string
  sub: string
  start: { label: string; href: string }
  /** the clip whose first frame is the card's still and whose loop plays on hover (public/media/<id>_*) */
  clip?: string
  /** the stills' own id when they are cut apart from the clip's posters (default: the clip's) */
  still?: string
  /** the clip's largest tier when it is a crop with less than 2560 native pixels: nothing larger is ever asked for */
  top?: Exclude<Tier, 'm'>
  alt: string
  widgets: Widget[]
}

const MARKET_LIST = MARKET_COORDS.map((m) => marketLabel(m.name))

export const ENTRY_CARDS: EntryCard[] = [
  {
    id: 'wild',
    tag: 'Story · Wild catch',
    title: 'Wild catch: from the sea to your table',
    cta: 'Enter the story',
    heading: 'Wild catch',
    sub: 'Marine fish from the fishing vessels, through our plant at Anandapuram, to the port.',
    start: { label: 'Start the story', href: '/story#ocean' },
    // hf-catch-card: a crop of the hf-catch master at its native pixels (scripts/encode-hf.sh SRC_CROP 1920:1080:640:0,
    // phone M_CROP 670:1192:1200:0) that leaves out the deck crates and the bin at the left edge in every frame
    clip: 'hf-catch-card',
    top: 1920,
    alt: 'On deck, the crew lean back and haul a dripping net of silver fish in over the rail, the open sea behind them.',
    widgets: [
      { label: 'Range', value: 'Marine fish', src: 53 },
      { label: 'Species', value: 'Indian Mackerel · Tuna · Seer Fish · Squid', src: 53 },
      { label: 'More species', value: 'Swordfish · Cuttlefish · Ribbon Fish · Leatherjacket', src: 53 },
      { label: 'States', value: 'Raw fresh · Chilled · Frozen', src: 67 },
      { label: 'Cold chain', value: 'Reefer containers to the destination', src: 47 },
      { label: 'Processed at', value: 'Anandapuram, Visakhapatnam', src: 35 },
    ],
  },
  {
    id: 'farmed',
    tag: 'Story · Farmed',
    title: 'Farmed shrimp',
    cta: 'Enter the story',
    heading: 'Farmed shrimp',
    sub: 'From partner farms, through our plant at Anandapuram, to the port.',
    start: { label: 'Start the story', href: '/story#pond' },
    // hf-sample, not hf-ponds: the ponds aerial has a truck mid-frame whose driving side can't be checked
    clip: 'hf-sample',
    // the card's own stills of hf-sample's first frame, each under 250 KB (scripts/stills.py CAP_KB=250); the clip's
    // 1920 poster is 326 KB
    still: 'hf-sample-card',
    alt: 'A farm technician crouches on the pond bank reading a handheld water meter, aerators churning the pond behind him.',
    widgets: [
      { label: 'Species', value: 'Vannamei · Black Tiger', src: 55 },
      { label: 'Partners', value: 'Strategic partnerships with aquaculture farmers', src: 29 },
      { label: 'Forms', value: 'Head-on · Headless · Peeled · Value-added', src: 41 },
      { label: 'Freezing', value: 'IQF or block frozen', src: 44 },
      { label: 'Cold storage', value: '−18 °C to −20 °C until dispatch', src: 46 },
      { label: 'States', value: 'Raw fresh · Chilled · Frozen', src: 67 },
    ],
  },
  {
    id: 'world',
    tag: 'Markets',
    title: 'From Visakhapatnam to the world',
    cta: 'Get a quote',
    heading: `Trusted in ${MARKET_COUNT} markets`,
    sub: `Based in ${ORIGIN.name}. Shipping in reefer containers keeps the cold chain to the destination.`,
    start: { label: 'Get a quote', href: '/quote' },
    alt: `Thin orbit lines from ${ORIGIN.name} to ${MARKET_COUNT} markets.`,
    // one widget per region (client's groups, CONTENT.md line 74)
    widgets: MARKETS_BY_REGION.map(({ region, markets }) => ({
      label: region,
      value: markets.map((i) => MARKET_LIST[i]).join(' · '),
      src: 74,
    })),
  },
]
