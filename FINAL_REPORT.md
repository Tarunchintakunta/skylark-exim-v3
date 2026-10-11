# FINAL_REPORT: Higgsfield story phase (#175)

Branch `feat/higgsfield-story` → `main`. Not merged; Tarun merges. Full per-take record: `HIGGSFIELD_LOG.md`.

## What is in it
- **20 Higgsfield clips (HS01–HS20)** replace the Blender stills and placeholder clips in every film chapter except `docs` (stays a still, #162) and the last sea segment (Blender `x-ship`, kept for the hand-off to the globe). Story beats and prompts: `docs/HIGGSFIELD_STORYBOARD.md`. Contact sheets (0/25/50/75/100 %): `docs/higgsfield/`.
- **One story with both origins.** The chosen path runs first, then the other origin, which opens with a bridge caption (eyebrow "Wild catch · Farmed", copy from CONTENT.md work flow step 1), then the plant, port, sea and globe. The path toggle still picks which origin comes first.
- **First screen:** a "What we export" line (Vannamei and Black Tiger shrimp · Marine fish · Raw fresh, chilled and frozen) and a Contact us button that scrolls to the RFQ section (`#quote`).
- **Weight (budgets unchanged):** every clip is trimmed to the 72 frames (3.0 s) its scroll segment needs, at the full clip's bitrate. Desktop takes the 1920 tier only above 1600 device px; phones scrub the 720 tier and prefetch only the next clip.
- **Joins:** segments inside a chapter cross-fade (separate shots never share a frame). HS13 → HS15 (peeling table into the lab) is one continuous move and uses the shared frame (boundary SSIM 0.96).
- **Cleanup:** replaced Blender stills (`a3_*`, `b2_*`) removed, posters within the per-file caps, no AVIF (nothing loads it), the sea name removed repo-wide (#173 / #174 merged in).
- `scripts/encode-hf.sh`: two-pass H.264 High, GOP 6, no B-frames, faststart, no audio, 24 fps; WebP posters within the caps.

## Scores (local, `vite preview` on port 5792 / `lhci autorun` on a random port, build f92a11f)
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

## Clips (72 frames, 3.0 s at 24 fps; before 124 frames, 5.17 s)
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

## Credits
Start 1910.75 → now 1066.75 (from `balance` calls): **844 spent** (images 364, video 480), 44 % of the start balance. The credit guard (1,624) was never reached.

## Coordinator re-verification (build 70f76d7, after the hero fix)
- **Hero fix:** cherry-picked 4dceb8f from #169 (fluid `--fs-hero`, `max-width: 100%`). Before it, "Visakhapatnam" was clipped at about 507 px wide on the preview. After it, nothing clips at 320, 375, 412, 507, 768, 1440 or 1920 px (checked in the browser at 375 and 507).
- **Playwright** (weight, boot, smoke): 13/13 pass.
  - Weight at the final build: desktop initial 1.41 MB and full scroll 24.29 MB; mobile initial 0.74–0.76 MB and full scroll 9.77 MB.
  - The full suite on 6be75f2 had 29/35 pass: the 5 `video-smoothness` failures plus `scroll-perf desktop ocean`, which is flaky when the whole suite runs. Run alone it passes 4/4 at 60 fps, p95 16.7 ms, 0 long tasks.
- **lhci on 70f76d7:** assertions pass. LCP 2,519 / 2,500 / 2,499 ms (median 2,500 ms, exactly on the limit). Perf 0.96, A11y 1.0.
- **GitHub Actions** still can't start jobs (account billing limit), so the red `ci` checks are not test results.

## Not done / open (Tarun's call)
- **LCP sits on the 2,500 ms limit** (median 2,500 ms; main 2,498–2,499 ms). Any heavier first screen will tip it over.
- **HS20 (hf-ship), text artefact: FAIL point.** The stern superstructure carries a small yellow placard with illegible pseudo-lettering, visible at 1920 from about 1.3 s to the end of the trimmed clip (the hull lettering of the full take is cut by the trim). A tracked blur over it left a visible smeared box, so it was not used. Fix options: one more take with "no lettering, no signs" (10 credits; the shot has used its 2 retakes), or accept it.
- **Seams:** only HS13 → HS15 is a shared-frame join. The nine other end-frame regenerations failed (cuts, dissolves, morphs), so those joins keep the 3 % poster cross-fade.
- **video-smoothness** stays red (see Scores); coldchain on mid Android needs a design change (fewer clips or a longer chapter), not an encode change.
- **Desktop tier:** a 1440-wide window now scrubs the 1280 tier (1.125x upscale); 1920 starts above 1600 device px.
- **Opening poster on phones** is a soft 6 KB frame, shown only until the clip paints (it sat on the LCP critical path at 36 KB).
- **Vercel preview:** https://skylark-exim-v3-git-hf-final-assembly-tarun-44555f1b.vercel.app/ built by the Vercel Git integration for PR #192 (status: success, HTTP 200). The hero, "What we export" and Contact us were checked there in a browser. No production deploy.
- `docs` chapter stays a still (#162). PR #176 (storyboard) is still open.
