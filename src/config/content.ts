// Every line here comes from docs/CONTENT.md ("Use on site" column) or docs/STORY.md.
// Headlines are editorial and make no factual claim. Do not add facts here that are not in CONTENT.md.

export interface CaptionCopy {
  eyebrow?: string
  title: string
  body?: string
  chips?: string[]
  /** small mono line instead of a body (x-ship) */
  note?: string
}

export const MARINE_FISH = ['Indian Mackerel', 'Tuna', 'Swordfish', 'Cuttlefish', 'Squid', 'Leatherjacket', 'Ribbon Fish', 'Seer Fish']
export const SHRIMPS = ['Vannamei', 'Black Tiger Shrimp', 'Sea White Shrimp', 'Pink / Brown', 'Sea Tiger Shrimp']
export const SHRIMP_CHIPS = ['Vannamei', 'Black Tiger', 'Sea White', 'Pink / Brown', 'Sea Tiger']
export const STATES = ['Raw fresh', 'Chilled', 'Frozen']

export const MARKETS = [
  'China', 'Europe', 'Vietnam', 'UAE (Sharjah)', 'Turkey', 'Thailand', 'Taiwan', 'Sri Lanka',
  'Malaysia', 'Kuwait', 'Japan', 'Egypt', 'Bangkok', 'Algeria', 'Russia', 'Hong Kong',
]

export const start = {
  eyebrow: 'Visakhapatnam · Andhra Pradesh',
  // confirm-list #3 fallback (the drafts' "Two Origins. One Standard." is not on skylarkexim.com)
  title: 'From the Bay of Bengal to the world.',
  body: 'Premium raw fresh, chilled and frozen seafood, with a fully integrated value chain from sourcing to delivery.',
  ocean: { label: 'The Ocean', sub: 'Wild catch' },
  pond: { label: 'The Pond', sub: 'Farmed shrimp' },
  skip: 'Skip the story',
  cta: 'Request export quote',
}

export const film: Record<string, CaptionCopy[]> = {
  o1: [{ eyebrow: 'The Ocean · 01', title: 'Before the harbour wakes.', body: 'Based in Visakhapatnam, Andhra Pradesh. Raw material is sourced directly from farms or fishing vessels.' }],
  o2: [{ eyebrow: 'The Ocean · 02', title: 'Out of the water.', body: 'Initial quality checks (size, freshness, health) are done before acceptance.' }],
  o3: [{ eyebrow: 'The Ocean · 03', title: 'On ice.', body: 'Premium raw fresh, chilled and frozen seafood.', chips: MARINE_FISH }],
  o4: [{ eyebrow: 'The Ocean · 04', title: 'Home under a chilled seal.', body: 'Transported under chilled conditions to the processing plant.' }],
  p1: [{ eyebrow: 'The Pond · 01', title: 'Partner farms on the Andhra coast.', body: 'Strategic partnerships with aquaculture farmers and a focus on responsible sourcing.' }],
  p2: [{ eyebrow: 'The Pond · 02', title: 'Every batch has a history.', body: 'We guarantee superior freshness, traceability, and product integrity across all markets.' }],
  p3: [{ eyebrow: 'The Pond · 03', title: 'Harvested into ice.', body: 'Shrimp are sourced directly from farms. Initial quality checks (size, freshness, health) are done before acceptance.', chips: SHRIMP_CHIPS }],
  intake: [{ eyebrow: 'The Plant · Anandapuram', title: 'Both origins arrive at one door.', body: 'Our processing unit at Anandapuram, Visakhapatnam: a state-of-the-art shrimp processing facility equipped with internationally acclaimed modernized equipment.' }],
  process: [
    { eyebrow: 'The Plant · Washing', title: 'Washed clean.', body: 'Thorough washing with clean, treated water to remove impurities.' },
    { eyebrow: 'The Plant · Grading', title: 'Graded to one standard.', body: 'Sorted by size, weight, and type. Grading ensures uniformity for export standards.' },
    { eyebrow: 'The Plant · Processing', title: 'Made to order.', body: 'De-heading, peeling and deveining, manual or machine, based on product requirement: Head-On, Headless, Peeled, or Value-Added.' },
  ],
  coldchain: [
    { eyebrow: 'The Plant · Quality lab', title: 'Tested before it moves.', body: 'Checks for hygiene, freshness, texture and absence of defects. Samples tested for international food safety compliance.' },
    { eyebrow: 'The Plant · Freezing', title: 'Frozen at its best.', body: 'IQF (Individually Quick Frozen) or block freezing. A thin ice glaze preserves freshness during shipment.' },
    { eyebrow: 'The Plant · Packing', title: 'Packed and labelled.', body: 'Export-grade cartons, vacuum packs, or customized packaging. Labels with product details, size, batch, and export compliance.' },
    { eyebrow: 'The Plant · Cold storage', title: 'Held at −18\u00a0°C to −20\u00a0°C.', body: 'Our warehouse has a total storage capacity of 700 pallets.' },
  ],
  docs: [{ eyebrow: 'Export · Documentation', title: 'Paperwork, done properly.', body: 'Our documentation staff professionally prepare all necessary documents and handle logistical tracking of shipments. Compliance with export certificates (HACCP, EU, FDA, etc.).' }],
  port: [{ eyebrow: 'Export · The port', title: 'Loaded under the cranes.', body: 'Shipped in reefer containers to maintain the cold chain until the destination.' }],
  sea: [{ eyebrow: 'Export · At sea', title: 'From Visakhapatnam to the world’s table.', note: 'Bay of Bengal · outbound' }],
  world: [{ eyebrow: 'Export · Markets', title: 'Trusted in 16 markets.', body: MARKETS.join(' · ') }],
}

/** Label card in the packing caption: field names only, never values (STORY §7). */
export const LABEL_FIELDS = ['Product', 'Size', 'Batch', 'Export compliance']
/** Documentation interlude cards (STORY §8): functions only, no document contents. */
export const DOC_CARDS = ['Export documents', 'Compliance (HACCP · EU · FDA)', 'Shipment tracking']

/** Why choose us (STORY §13; tile lines from CONTENT.md "Use on site"). */
export const TRUST = {
  title: 'Why choose us',
  tiles: [
    { title: 'Quality control staff', line: 'For our clients, our quality control staff guarantee top-notch quality.' },
    { title: 'Lab unit', line: 'Our lab unit at Anandapuram, Visakhapatnam.' },
    { title: 'Traceability', line: 'Superior freshness, traceability and product integrity across all markets.' },
    { title: 'Documentation staff', line: 'Our documentation staff prepare all necessary documents and track every shipment’s logistics.' },
    { title: 'Farmer partnerships', line: 'Strategic partnerships with aquaculture farmers and a focus on responsible sourcing.' },
    { title: 'Prompt delivery', line: 'Competent people for accurate order handling and prompt delivery.' },
  ],
  compliance: 'Compliance with export certificates (HACCP, EU, FDA, etc.)',
  facts: [
    { value: '700', label: 'pallet warehouse' },
    { value: '16', label: 'markets' },
    { value: 'Raw fresh, chilled and frozen', label: 'seafood' },
  ],
}
