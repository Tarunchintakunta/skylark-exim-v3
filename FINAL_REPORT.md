# FINAL_REPORT: Skylark Exim v3, combined final round (12 Oct 2026)

Branch `feat/higgsfield-story` goes to `main` through **#193**. #193 is not merged; Tarun merges it. Nothing was pushed or merged to `main`.

## Shareable URL (no Vercel login)
**https://skylark-exim-v3-git-feat-higgsfield-story-tarun-44555f1b.vercel.app**

- **Build:** the Git-triggered Vercel preview of `feat/higgsfield-story` at **202611c** (Merge #221). It has every change below; this report PR is docs only.
- **Immutable URL for the same build:** https://skylark-exim-v3-c316m2nip-tarun-44555f1b.vercel.app
- **Logged-out check:** `curl` and fresh Playwright contexts with no cookies get 200 for `/`, `/quote`, `/news` and the media files.
- **Specs against the preview:** smoke, separate-paths, pages and path-anchors give 31/32 on the first, cold run. On a warm CDN, separate-paths gives 16/16 (×2 repeats). See Unfinished #1.

## Merged into `feat/higgsfield-story` this round
Each PR was merged with a merge commit after its **merged state** passed typecheck, build and the Playwright suite. The only failures were the known throttled `video-smoothness` profiles (see Unfinished #3). Merge order F was #215 → A → C → B → D → E.

| Order | PR | What |
|---|---|---|
| 1 | #215 | `vercel.json`: `/news/:slug` rewrites to `/news` (#214) |
| 2 | #220 | **A.** Wild catch and Farmed shrimp are two separate stories (#219) |
| 3 | #226 | **C.** Pond retakes: hf-sample (handheld meter, probe on a cable) and hf-harvest (crew behind the drag net, floats in front, crates and ice boxes on the bank, plain white truck) (#224) |
| 4 | #227 | **B.** Wild path: fish in the plant. hf-fish-intake, hf-fish-wash, hf-fish-cut and hf-fish-freeze in `sharedFor('ocean')`, with fact-only captions (#225) |
| 5 | #223 | **D.** Globe loads fast: placeholder image, idle prefetch, smaller textures, DPR cap 1.5 (#222) |
| 6 | #221 | **E.** Intro loader (#218), built by the peer session. It buffers only the chosen path's first clip. Merged with Tarun's OK |

## Per-path chapters, clips and captions
Every caption quotes skylarkexim.com (docs/CONTENT.md). The wild path has no shrimp clip or text in the film. Its only mention is the link over to the other story at the end of coldchain. `tests/separate-paths.spec.ts` asserts this.

**Wild catch (`/#ocean`)**

| # | chapter | clips | captions (title: body) |
|---|---|---|---|
| 0 | start | opening | – |
| 1 | o1 | hf-depart | Before the harbour wakes.: Based in Visakhapatnam, Andhra Pradesh. Raw material is sourced directly from farms or fishing vessels. |
| 2 | o2 | hf-catch | Out of the water.: Initial quality checks (size, freshness, health) are done before acceptance. |
| 3 | o3 | hf-ice | On ice.: Premium raw fresh, chilled and frozen seafood. |
| 4 | o4 | hf-return | Home under a chilled seal.: Transported under chilled conditions to the processing plant. |
| 5 | intake | hf-arrive → hf-fish-intake | Into the plant.: Transported under chilled conditions to our processing unit at Anandapuram, Visakhapatnam. Initial quality checks (size, freshness, health) are done before acceptance. |
| 6 | process | hf-fish-wash → hf-fish-cut | Washed and graded.: Thorough washing with clean, treated water to remove impurities. Sorted by size, weight and type. Grading ensures uniformity for export standards. / One standard, every stage.: Our commitment to excellence is powered by advanced processing facilities, innovative technology, and strict adherence to international quality standards. |
| 7 | coldchain | hf-fish-freeze → hf-store | Frozen at its best.: IQF (Individually Quick Frozen) or block freezing. Glazing (a thin ice layer) applied to preserve freshness during shipment. / Held cold until dispatch.: Our warehouse has a total storage capacity of 700 pallets. |
| 8 | docs | ph-docs | Paperwork, done properly.: Our documentation staff professionally prepare all necessary documents and handle logistical tracking of shipments. Compliance with export certificates (HACCP, EU, FDA, etc.). |
| 9 | port | hf-stuff → hf-cranes | Loaded under the cranes.: Shipped in reefer containers to maintain the cold chain until the destination. |
| 10 | sea | hf-ship → hf-sail | From Visakhapatnam to the world’s table. |
| 11 | world | globe | Trusted in 15 markets. |

**Farmed shrimp (`/#pond`)**

| # | chapter | clips | captions (title: body) |
|---|---|---|---|
| 0 | start | opening | – |
| 1 | p1 | hf-ponds | Partner farms on the Andhra coast.: Strategic partnerships with aquaculture farmers and a focus on responsible sourcing. |
| 2 | p2 | hf-sample | Every batch has a history.: We guarantee superior freshness, traceability, and product integrity across all markets. |
| 3 | p3 | hf-harvest → hf-sort | Harvested into ice.: Shrimp are sourced directly from farms. Initial quality checks (size, freshness, health) are done before acceptance. |
| 4 | intake | hf-arrive → hf-intake | Into the plant.: Our processing unit at Anandapuram, Visakhapatnam: a state-of-the-art shrimp processing facility equipped with internationally acclaimed modernized equipment. |
| 5 | process | hf-wash → hf-peel | Washed clean.: Thorough washing with clean, treated water to remove impurities. / Graded to one standard.: Sorted by size, weight, and type. Grading ensures uniformity for export standards. / Made to order.: De-heading, peeling and deveining, manual or machine, based on product requirement: Head-On, Headless, Peeled, or Value-Added. |
| 6 | coldchain | hf-lab → hf-iqf → hf-pack → hf-store | Tested before it moves.: Checks for hygiene, freshness, texture and absence of defects. Samples tested for international food safety compliance. / Frozen at its best.: IQF (Individually Quick Frozen) or block freezing. Glazing (a thin ice layer) applied to preserve freshness during shipment. / Packed and labelled.: Export-grade cartons, vacuum packs, or customized packaging. Labels with product details, size, batch, and export compliance. / Held at −18 °C to −20 °C.: Our warehouse has a total storage capacity of 700 pallets. |
| 7 | docs | ph-docs | Paperwork, done properly.: Our documentation staff professionally prepare all necessary documents and handle logistical tracking of shipments. Compliance with export certificates (HACCP, EU, FDA, etc.). |
| 8 | port | hf-stuff → hf-cranes | Loaded under the cranes.: Shipped in reefer containers to maintain the cold chain until the destination. |
| 9 | sea | hf-ship → hf-sail | From Visakhapatnam to the world’s table. |
| 10 | world | globe | Trusted in 15 markets. |

## Full re-verify (G), merged tip 202611c, local `vite preview`, real GPU (`GPU=1`) where noted
| Gate | Target | Before this round (f44dc92) | Now |
|---|---|---|---|
| `tsc`, `npm run build` (homepage + /quote + /news) | pass | pass | pass |
| Playwright suite (78 tests, incl. new `separate-paths` and `globe-load`) | green | 51/51 outside `video-smoothness` | **74/78**. The 4 failures are the throttled `video-smoothness` profiles (Unfinished #3) |
| `video-smoothness` desktop ocean / pond (GPU) | ≥ 20 fps, seek p95 ≤ 50 ms | pass | **pass** (2/2) |
| `scroll-perf` (GPU, 1 worker) | 60 fps, 0 long tasks | 60 fps, 0 long tasks | **60 fps, p95 16.7–16.8 ms, 0 long tasks**, desktop and mobile, both paths, 2 runs |
| Lighthouse **mobile**, 3 runs × 3 pages | Perf ≥ 90, A11y ≥ 95, LCP ≤ 2,500, CLS 0 | Home Perf 96–97, LCP 2,257–2,445 ms | Home **Perf 96–97, A11y 100, LCP 2,256 / 2,403 / 2,411 ms**, CLS 0, TBT 0. `/quote` Perf 98, LCP 2,104 ms. `/news` Perf 99, LCP 1,802–1,807 ms |
| Lighthouse **desktop**, 3 runs × 3 pages | same | Home Perf 99, LCP 609–613 ms | Home **Perf 100, A11y 100, LCP 524–566 ms**. `/quote` and `/news` Perf 100, LCP 442–445 ms. CLS 0 everywhere |
| Initial load, desktop / mobile | ≤ 3 MB / ≤ 1.5 MB | 2.03 / 0.84 MB | ocean **2.03 / 0.84 MB**, pond **2.01 / 0.85 MB** |
| Full scroll per path, desktop / mobile | ≤ 25 MB / ≤ 12 MB | 22.87 / 8.86 MB (one shared story) | ocean **16.81 / 6.59 MB**, pond **18.47 / 7.26 MB** |
| Every file | ≤ 2,300 KB | pass | pass. The new clips are 1,266–1,483 KB at 1920 |
| Console errors | 0 | 0 | **0** on both paths at 390, 1024 and 1440 |

**Globe load time (D)**, measured by `tests/globe-load.spec.ts` from the moment Markets is shown:
| | Before | After: picture on screen | After: live WebGL frame |
|---|---|---|---|
| Desktop 1440 | 589–639 ms | **0 ms** (placeholder, crossfades to the live globe) | 570–572 ms |
| Phone, slow 4G, 4× CPU | about 6.2 s | **0 ms** | 3.85–3.86 s |

The visible globe meets the 300 / 800 ms targets via the ≤ 60 KB placeholder (11 KB / 5 KB). The live, draggable frame does not (Unfinished #2). Textures: 33 KB (phone, 1024) and 117 KB (desktop, 2048), both ≤ 300 KB.

**Manual pass (390, 1024, 1440; both paths)**, one frame per chapter at 45 % of its scroll plus the business sections:
- Sheets are in `docs/review/final-r3/sheet-{390,1024,1440}-{ocean,pond}.jpg`.
- The wild path shows the fish plant: truck → washed and graded → frozen. The pond path shows the new p2 and p3.
- No overlaps; the 1024 header has Menu and "Request export quote" side by side.

## Contact sheets (3 start-frame candidates per shot)
- Pond retakes: `docs/review/retakes/sheet-sample.jpg`, `sheet-harvest.jpg`.
- Fish plant: `docs/review/fish/sheet-{fintake,fwash,fcut,ffreeze}.jpg`.
- The picks, trims and reasons are in HIGGSFIELD_LOG.md (2026-10-12).

## Higgsfield credits
- From `balance`: 1,910.75 at the start, 474.75 now, so **1,436 used**. The 1,624 guard was not reached.
- This round: 270 for 18 start frames (gpt_image_2_5 at max 4k costs 15 per image, not 15 per job as planned), plus 60 for 6 videos (minimax_h3 2K, 5 s).
- minimax_h3 at 4 s failed twice and was refunded; 5 s works.

## Brief deviations
- **Pomfret** (brief B) is on the CONTENT.md never-write list, so the fish shots use tuna, seer fish and Indian mackerel.
- **"Blast freezing"** is on the never-write list too. The freeze caption quotes the site's IQF / block freezing and glazing text.
- **Pond freezing caption** now quotes CONTENT.md word for word ("Glazing (a thin ice layer) applied…") instead of a paraphrase.

## Unfinished
1. **Cold-cache deep link.**
   - On the first cold-CDN run against the preview, `separate-paths` "/#pond is the farmed-shrimp story only" failed 3/3: the page stayed at the top instead of landing on p1.
   - Every later run passes: 16/16 in the spec, 8/8 in a manual trace, and locally always.
   - It looks like a race between the loader's hand-off and the jump on a slow first load. Not fixed.
2. **Live globe frame.** The live frame takes 570 ms on desktop and 3.85 s on a throttled phone, against the 300 / 800 ms targets. The placeholder covers the gap visually. A faster live frame needs a smaller Three chunk or an earlier idle import.
3. **Throttled `video-smoothness`** (`desktop-fast4g`, `android-mid`) stays red, as in the previous rounds. Fixing it needs a design change (fewer clips per chapter or longer chapters).
4. **Swordfish product still**: not regenerated.

## Tarun to decide
- **Merge #193 to `main`** to go live. Production stays on `main`; no production deploy was made.
- Whether the cold-cache deep-link race (Unfinished #1) blocks go-live.

---

## Previous round: overnight final run (11–12 Oct 2026)

Branch `feat/higgsfield-story` → `main` through **#193**. #193 is not merged; Tarun merges it.

### Shareable URL (no Vercel login)
**https://skylark-exim-v3-git-feat-higgsfield-story-tarun-44555f1b.vercel.app**

- **Commit:** this branch alias serves `feat/higgsfield-story` at **f44dc92**, which has every code change below. The only later commit is this report, which is docs only.
- **Immutable URL for the same build:** https://skylark-exim-v3-ixdi3wh0n-tarun-44555f1b.vercel.app
- **No login wall.** Checked logged out with `curl` and fresh Playwright contexts (no cookies): `/`, `/#ocean`, `/#pond`, `/quote`, `/news` and the media files all return 200. Deployment protection is off for previews, so there's no setting to change.
- **Deploy limit:** Vercel's free-tier limit (100/day) was hit after f44dc92. Later pushes show "Deployment rate limited — retry in 24 hours". The alias stays on f44dc92 until a deploy succeeds. I didn't retry, to avoid piling up failed deploys.

### Merged into `feat/higgsfield-story` tonight
Each PR was merged with a merge commit, only after its **merged state** passed typecheck, build and the Playwright suite. Conflicts were resolved on the PR branch, keeping both sides.

| Order | PR | What | Conflicts resolved |
|---|---|---|---|
| 1 | #201 | Markets: 15 markets (Bangkok dropped), quieter globe, region grid (#194) | – |
| 2 | #202 | Products: photoreal stills replace the 3D tuna turntable (#195) | – |
| 3 | #204 | Header path toggle never overlaps the nav at 900–1199 px (#203) | – |
| 4 | #199 | Globe: drag to rotate, click a market to face it, ease home when idle (#198) | Globe.tsx, Extras.tsx (see below) |
| 5 | #205 | Looping hero video, hand-off into the story, headline fit (#197) | – |
| 6 | #211 | `/#ocean`, `/#pond` and both toggles land on their own chapter; no stale caption after a path switch (#210) | ChapterCopy.tsx, scrub.ts |
| 7 | #208 | Docs chapter desk photo; leftover-Blender audit, HS21 replaces x-ship (#196) | ScrubStage.tsx, stage.css |
| 8 | #206 | `/quote` and `/news` pages, closing band, new navbar (#200) | App.tsx |
| 9 | #209 | LCP: static hero copy before JS, lazy story chunk (#207) | index.html, App.tsx, Hero.tsx, vite.config.ts |
| 10 | #213 | `video-smoothness`: the start chapter is not a stage still (#212) | – |

- **#199 conflict:** the markets PR rewrote the globe (layout from the caption box, label overlay, idle region tour). The drag, keys, inertia, click-to-face and ease-home were ported onto that version. The tour pauses while the visitor is in control, and drag speed follows the globe's on-screen radius.
- **#206 conflict:** App.tsx keeps both hash effects: #210's `#ocean`/`#pond` binding and #200's jump to a section anchor arriving from `/quote` or `/news`.

#### What the brief asked for, and where it is
- **a. Ocean/pond (#211).**
  - `/#ocean` and Wild catch land on o1, the wild-catch boat chapter. `/#pond` and Farmed shrimp land on p1, the ponds.
  - `tests/path-anchors.spec.ts` has 8 tests: deep links on desktop and Pixel 7, both header toggles, a same-page hash change, and every chapter's clip and copy on both paths. 8/8 pass on the final branch.
  - The manual walk below repeats the clip → copy check at 3 widths.
- **b. Docs and the Blender audit (#208).**
  - Docs now has a readable desk photo.
  - Audit: every chapter at 1440 and 390, both paths, at 30 % and 75 % of each chapter. The only leftover was the Blender x-ship at the end of sea, now replaced by HS21.
  - My final walk found no Blender visuals: no `x-cranes`/`x-ship`/`ph-*` references in `src`, and no GLB is loaded. The four logistics GLBs (truck, reefer, crane, ship) remain in `public/models` but nothing references them.
- **c. Quote and news (#206).**
  - The form lives at `/quote`. The navbar "Request export quote →", the hero "Contact us", the closing band, the contact band and the mobile bar all link to `/quote`.
  - `/news` is "News & updates", built from `src/content/news.json`.
    - The file is empty, because skylarkexim.com has no real news. Its `/blog-news/` page is spam.
    - The page says "Updates coming soon" and links to `/quote`.
    - `src/content/NEWS.md` has a template for adding posts.
  - The homepage ends with the closing band, the contact band and the footer.
  - Navbar order: Story, Products, About, News, Contact, Request export quote →.
  - Each page has its own title, meta description and canonical.
- **d. LCP (#209).**
  - The hero headline, body, export line and links are static HTML in `index.html`, with inline critical CSS generated from `content.ts`, `tokens.css` and `hero.css`. React's hero takes over at the identical position.
  - The copy sits above the loader, because Chrome ignores occluded text for LCP. The loader mark moved into the space above the copy.
  - Story, captions and the business sections are a lazy chunk (Three and the globe already were).
  - The homepage's 4 kB stylesheet is inlined.
  - Fonts are `display: block` and preloaded, so CLS is 0.
- **e. Swordfish still: not regenerated.** This session has no authenticated Higgsfield connector, and the other session wouldn't spend credits on a relayed brief. It still needs a regen. "Pink / Brown" in the p3 species list is kept as is; flagged below.

### Full re-verify on the final branch (f44dc92, local `vite preview` + real GPU where noted)
| Gate | Target | Result |
|---|---|---|
| `tsc`, `npm run build` (homepage + /quote + /news) | pass | pass |
| Playwright suite (57 tests) | green | **51/51 pass** outside `video-smoothness` (smoke, boot, captions, chrome, globe-drag, globe-labels, path-anchors, pages, prefetch, media-urls, stage-reset, weight, headline). `video-smoothness`: see below |
| `scroll-perf` (GPU=1) | 60 fps, 0 long tasks | desktop ocean/pond and mobile ocean/pond (4× CPU): **60 fps, p95 16.7–16.8 ms, 0 long tasks** |
| Lighthouse **mobile**, 3 runs × 3 pages | Perf ≥ 90, A11y ≥ 95, LCP ≤ 2,500 | Home: Perf 96–97, A11y 100, BP 100, SEO 100, **LCP 2,257 / 2,260 / 2,445 ms**, CLS 0, TBT 0. `/quote`: Perf 98, LCP 2,103–2,110 ms. `/news`: Perf 99, LCP 1,802 ms |
| Lighthouse **desktop**, 3 runs × 3 pages | same | Home: Perf 99, A11y 100, LCP 609–613 ms. `/quote` and `/news`: Perf 100, LCP 443–445 ms. CLS 0 everywhere |
| Initial load | ≤ 3 MB desktop / ≤ 1.5 MB mobile | **2.03 / 0.84 MB** |
| Full scroll | ≤ 25 MB / ≤ 12 MB | **22.87 / 8.86 MB** |
| Every file | ≤ 2,300 KB | largest is the company profile PDF (2,064 KB); the largest clip is `hf-ship_1920.mp4` (1,766 KB) |
| Console errors | 0 | **0** across every chapter on both paths at 390, 1024 and 1440, plus `/quote` and `/news` |
| Banned claims (CONTENT.md "Never write" list, "Bay of Bengal") | none | none in `src`, `index.html`, `quote.html` or `news.html` |
| Vercel preview (logged out) | smoke | smoke, pages, path-anchors and globe-drag against the preview: 24/25 pass. The one failure is `/news/:slug` (see Unfinished) |

**LCP before and after (mobile, same machine).**
- Before (base 3d5b956): 2,527–2,573 ms. The LCP element was React's `p.hero__body`, shown at the loader reveal.
- After: median 2,257 ms. The LCP element is the static copy, and observed LCP is under 50 ms in every run.
- About 1 run in 3 simulates at 2.43–2.45 s, because Lantern counts the in-flight font requests. That's still under the 2,500 ms hard limit, but not always under the 2,300 ms target.

**`video-smoothness` (real GPU):**
- **Desktop ocean and pond: pass.** Every chapter presents 37–60 fps, with seek p95 ≤ 9 ms.
- **Throttled profiles still fail:** `desktop-fast4g` (fast 4G) and `android-mid` (4× CPU, 720 tier) miss the stale-%, fps and seek limits in several chapters. They failed the same way on the base build before tonight's merges. Only a design change fixes this (fewer clips per chapter or longer chapters). It isn't a regression.

### Screenshots
- **Before / after, first screen at 1.5 s on slow 4G:**
  - Before: `docs/review/lcp/before-390-at-1500ms-slow4g.png` and `before-1440-…` show only the loader.
  - After: `after-390-…` and `after-1440-…` show the headline and body.
- **Every chapter in order, at 45 % of each chapter, plus the business sections:**
  - `docs/review/final/sheet-1440-ocean.jpg`, `sheet-1440-pond.jpg`
  - `sheet-1024-pond.jpg`
  - `sheet-390-ocean.jpg`, `sheet-390-pond.jpg`
- **`/quote` and `/news` at 390, 1024 and 1440:** `docs/review/final/sheet-pages.jpg`.
- **Earlier before/after shots:** each merged PR has its own under `docs/review/` and `docs/higgsfield/`.

### Unfinished, and why
1. **`/news/:slug` returns 404 on Vercel.** The fix is PR #215 (#214), held open.
   - Cause: `cleanUrls` serves `news.html` at `/news`, so the old rewrite to `/news.html` doesn't resolve.
   - It can't be checked on a preview until the Vercel deploy limit resets. Once a deploy succeeds, run `BASE_URL=<preview> npx playwright test tests/pages.spec.ts`, then merge.
   - Impact today is small: no news posts exist, so only a hand-typed `/news/anything` URL hits it.
2. **Swordfish still** (3e) wasn't regenerated (no Higgsfield access in this session).
3. **Throttled `video-smoothness` profiles** stay red (see above).
4. **Port 1080p Blender render:** finished (479 frames, 47 min) but not used. #208 replaced x-ship with HS21, and the port chapter uses Higgsfield clips. The frames stay in `assets-src/render/port/`, which isn't committed.

### Tarun to decide
- **Merge #193 to `main`** to go live. Production stays on `main`, and no production deploy was made.
- **Swordfish still:** regenerate it (no illustrated sheen), or keep it.
- **"Pink / Brown"** in the pond species line (p3: "Vannamei · Black Tiger · Sea White · Pink / Brown · Sea Tiger"): kept as is, as the brief asked. It reads like a colour, not a species name, so please confirm the wording against skylarkexim.com.
- **#215:** merge after the preview check above.
- **GitHub Actions** jobs don't start (account billing / spending limit), so every red `ci` check is that, not a test result. Fix it under Settings → Billing & plans.
- **Higgsfield credits** (shared account, last ledger from the other session): 1,106 spent, balance 804.75. The 1,624 guard was never reached. This session spent 0.

---

## Earlier report: Higgsfield story phase (#175)

_Kept for history. The numbers below predate tonight's merges; the current state is above._

Branch `feat/higgsfield-story` → `main`. Not merged; Tarun merges. Full per-take record: `HIGGSFIELD_LOG.md`.

#### What is in it
- **20 Higgsfield clips (HS01–HS20)** replace the Blender stills and placeholder clips in every film chapter except `docs` (stays a still, #162) and the last sea segment (Blender `x-ship`, kept for the hand-off to the globe). Story beats and prompts: `docs/HIGGSFIELD_STORYBOARD.md`. Contact sheets (0/25/50/75/100 %): `docs/higgsfield/`.
- **One story with both origins.** The chosen path runs first, then the other origin, which opens with a bridge caption (eyebrow "Wild catch · Farmed", copy from CONTENT.md work flow step 1), then the plant, port, sea and globe. The path toggle still picks which origin comes first.
- **First screen:** a "What we export" line (Vannamei and Black Tiger shrimp · Marine fish · Raw fresh, chilled and frozen) and a Contact us button that scrolls to the RFQ section (`#quote`).
- **Weight (budgets unchanged):** every clip is trimmed to the 72 frames (3.0 s) its scroll segment needs, at the full clip's bitrate. Desktop takes the 1920 tier only above 1600 device px; phones scrub the 720 tier and prefetch only the next clip.
- **Joins:** segments inside a chapter cross-fade (separate shots never share a frame). HS13 → HS15 (peeling table into the lab) is one continuous move and uses the shared frame (boundary SSIM 0.96).
- **Cleanup:** replaced Blender stills (`a3_*`, `b2_*`) removed, posters within the per-file caps, no AVIF (nothing loads it), the sea name removed repo-wide (#173 / #174 merged in).
- `scripts/encode-hf.sh`: two-pass H.264 High, GOP 6, no B-frames, faststart, no audio, 24 fps; WebP posters within the caps.

#### Scores (local, `vite preview` on port 5792 / `lhci autorun` on a random port, build f92a11f)
| Gate | Target | Result |
|---|---|---|
| `npm run typecheck`, `npm run build` | pass | pass |
| Playwright | green | **30 of 35 pass**; the 5 failures are `video-smoothness` (6 failed on main 861f0f1), see below |
| Lighthouse (mobile, 3 runs) | Perf >= 90, A11y >= 95, LCP <= 2,500 ms | Perf 95-96, A11y 100, Best practices 100, SEO 90, CLS 0; LCP 2,499 / 2,502 / 2,510 ms (assertion passes; main 861f0f1 measures 2,498-2,499 ms, so this sits on the limit, as main does) |
| Initial load | <= 3 MB desktop / <= 1.5 MB mobile | 1.41 MB / 0.74-0.76 MB |
| Full scroll | <= 25 MB desktop / <= 12 MB mobile | 24.29 MB / 9.77 MB |
| Per-file caps (weight.spec) | all files | pass |
| Scroll (desktop) | 60 fps | rAF 60 fps, 0 long tasks; scroll-perf spec passes |
| banned sea-name grep (#173) | no matches | no matches |

**video-smoothness (still failing, as on main).** rAF stays at 57-60 fps on every profile (no page jank); what falls short is the clip's presented frame rate in some chapters:
- desktop (no throttling): o3 and p2 (100 vh chapters, under 1 s of scroll in the test) show the poster while the clip is still loading (stale 48-61 %, 11-25 fps); every other chapter 34-60 fps.
- android-mid (4x CPU, 720 tier): coldchain 14-15 fps, process 16, o3 17-19, p3 17, intake 16-19, sea 19-20; the rest 22-66. A GOP-12 720 tier and a 540p tier were both measured for coldchain/p3/port and did not lift coldchain (14.5-15.2 fps either way), so it is not decode-bound; it is the four clips in 240 vh switching decoders. Not changed.

#### Clips (72 frames, 3.0 s at 24 fps; before 124 frames, 5.17 s)
SSIM = 1920 tier vs the trimmed master. Sizes in KB, tiers 1920/1280/960/720.

| Chapter | Shot | Clip | Frames kept | SSIM | KB |
|---|---|---|---|---|---|
| start | HS01 take2 | opening | 0-71 | 0.967 | 1343/839/496/318 |
| o1 | HS02 take1 | hf-depart | 0-71 | 0.918 | 1426/879/512/320 |
| o2 | HS03 take3 | hf-catch | 0-71 | 0.846 | 1467/912/534/330 |
| o3 | HS04 take2 | hf-ice | 0-71 | 0.849 | 1399/868/517/326 |
| o4 | HS05 take1 | hf-return | 0-71 | 0.891 | 1452/893/518/323 |
| p1 | HS06 take2 | hf-ponds | 0-71 | 0.905 | 1376/847/502/321 |
| p2 | HS09 take1 | hf-sample | 50-121 | 0.931 | 1336/835/499/320 |
| p3 | HS07 take2 | hf-harvest | 0-71 | 0.882 | 1444/891/523/327 |
| p3 | HS08 take2 | hf-sort | 0-71 | 0.858 | 1365/853/517/330 |
| intake | HS10 take2 | hf-arrive | 52-123 | 0.931 | 1315/820/496/318 |
| intake | HS11 take1 | hf-intake | 52-123 | 0.960 | 1309/818/489/315 |
| process | HS12 take1 | hf-wash | 0-71 | 0.934 | 1306/825/495/319 |
| process | HS13 takeS1 | hf-peel | 52-123 | 0.982 | 1306/819/487/313 |
| coldchain | HS15 take1 | hf-lab | 0-71 | 0.985 | 1274/794/479/311 |
| coldchain | HS14 take1 | hf-iqf | 0-71 | 0.938 | 1289/809/491/317 |
| coldchain | HS16 take1 | hf-pack | 52-123 | 0.983 | 1293/809/487/313 |
| coldchain | HS17 take1 | hf-store | 52-123 | 0.961 | 1327/828/495/316 |
| port | HS18 take1 | hf-stuff | 33-104 | 0.945 | 1309/824/495/317 |
| port | HS19 take2 | hf-cranes | 0-71 | 0.937 | 1297/826/499/320 |
| sea | HS20 take4 | hf-ship | 0-71 | 0.826 | 1766/1083/625/388 |

Totals: 1920 tier 28.1 MB, 1280 17.5 MB, 960 10.4 MB, 720 6.6 MB (20 clips).

#### Credits
Start 1910.75 → now 1066.75 (from `balance` calls): **844 spent** (images 364, video 480), 44 % of the start balance. The credit guard (1,624) was never reached.

#### Coordinator re-verification (build 70f76d7, after the hero fix)
- **Hero fix:** cherry-picked 4dceb8f from #169 (fluid `--fs-hero`, `max-width: 100%`). Before it, "Visakhapatnam" was clipped at about 507 px wide on the preview. After it, nothing clips at 320, 375, 412, 507, 768, 1440 or 1920 px (checked in the browser at 375 and 507).
- **Playwright** (weight, boot, smoke): 13/13 pass.
  - Weight at the final build: desktop initial 1.41 MB and full scroll 24.29 MB; mobile initial 0.74–0.76 MB and full scroll 9.77 MB.
  - The full suite on 6be75f2 had 29/35 pass: the 5 `video-smoothness` failures plus `scroll-perf desktop ocean`, which is flaky when the whole suite runs. Run alone it passes 4/4 at 60 fps, p95 16.7 ms, 0 long tasks.
- **lhci on 70f76d7:** assertions pass. LCP 2,519 / 2,500 / 2,499 ms (median 2,500 ms, exactly on the limit). Perf 0.96, A11y 1.0.
- **GitHub Actions** still can't start jobs (account billing limit), so the red `ci` checks are not test results.

#### Not done / open (Tarun's call)
- **LCP sits on the 2,500 ms limit** (median 2,500 ms; main 2,498–2,499 ms). Any heavier first screen will tip it over.
- **HS20 (hf-ship), text artefact: FAIL point.** The stern superstructure carries a small yellow placard with illegible pseudo-lettering, visible at 1920 from about 1.3 s to the end of the trimmed clip (the hull lettering of the full take is cut by the trim). A tracked blur over it left a visible smeared box, so it was not used. Fix options: one more take with "no lettering, no signs" (10 credits; the shot has used its 2 retakes), or accept it.
- **Seams:** only HS13 → HS15 is a shared-frame join. The nine other end-frame regenerations failed (cuts, dissolves, morphs), so those joins keep the 3 % poster cross-fade.
- **video-smoothness** stays red (see Scores); coldchain on mid Android needs a design change (fewer clips or a longer chapter), not an encode change.
- **Desktop tier:** a 1440-wide window now scrubs the 1280 tier (1.125x upscale); 1920 starts above 1600 device px.
- **Opening poster on phones** is a soft 6 KB frame, shown only until the clip paints (it sat on the LCP critical path at 36 KB).
- **Vercel preview:** https://skylark-exim-v3-git-hf-final-assembly-tarun-44555f1b.vercel.app/ serves commit **6be75f2**, the assembly *before* the hero fix. On it, the hero, "What we export" and Contact us were checked in a browser, and the "Visakhapatnam" clip at ~507 px was found there. Every later commit (70f76d7 hero fix, b91f3fb, 8846fd6) hit Vercel's free-tier daily deploy limit ("Deployment rate limited — retry in 24 hours"), so the hero fix has only been verified locally on port 5792. Redeploy once the limit resets. No production deploy.
- `docs` chapter stays a still (#162). PR #176 (storyboard) is still open.

#### Follow-up (2026-10-11 evening): #196 and #197
- **#196 (PR on `hf/196-docs-audit`):**
  - Docs chapter: a readable export-office desk photo (gpt_image_2_5) with a light blur and the stage's left and bottom scrims. On phones the photo is dimmed so the copy keeps AA. Contrast was measured against the brightest 5 % of background pixels under each text run:

    | Width | Eyebrow | Title | Body | List |
    |---|---|---|---|---|
    | 1440 px | 6.6 | 8.3 | 14.8 | 15.0+ |
    | 390 px | 4.7 | 8.8 | 10.1 | 15.0+ |

  - Docs image size: 1280 = 37 KB, 720 = 15 KB.
  - Audit at 1440 and 390 px found one more leftover: the Blender x-ship clip at the end of the sea chapter. It is replaced by HS21 (photoreal, continues from HS20's last frame).
  - Results: Playwright 28/35 on the full run. `scroll-perf` desktop pond failed under load and passed 4/4 when run alone. `video-smoothness` still fails (6), as on main.
  - Weight: initial 1.41 / 0.76 MB, full scroll 24.02 / 9.55 MB.
  - Lighthouse mobile: Perf 96, A11y 100, LCP 2.50 s.
- **#197 (PR #205):**
  - A seamless 6 s coastal hero loop (HS01, cross-dissolved seam) that dissolves into the scrubbed story on scroll.
  - Headline sized by the column, with a glyph-extent test from 320 to 2560 px.
  - Weight: initial 1.75 / 0.79 MB, full scroll 24.86 / 10.01 MB.
  - **LCP 2.50 s, not below 2.3 s.** Render delay is about 2.0 s of main-JS execution (135 KB gz, 4x CPU). Removing the loader's hold on the hero text did not change it. Options are in PR #205.
- Credits: 37 for these (12 hero loop, 15 docs image, 10 HS21). See HIGGSFIELD_LOG.md for the shared-account spend.

Ready for Tarun to merge #193 to go live.
