# 3_DAY_PLAN.md

Tarun and Claude work in parallel. Claude never waits for assets (placeholders, CLAUDE_PROMPT §6); each asset Tarun delivers is swapped in through its own small PR.

## Day 1
**Tarun**
1. Answer `confirm-list.md` (5 minutes; any unanswered item uses its fallback).
2. Top up Higgsfield credits (last ledger balance 160; plan needs ~830, budget 1,100–1,200).
3. Clone github.com/Tarunchintakunta/skylark (anchors are in `assets/anchors`, `assets/stills`). Extract `a3_first_1080.png` (command in HIGGSFIELD_PROMPTS.md §1).
4. Higgsfield 720p drafts for the two must-haves and the riskiest: **o-catch**, **p-proc**, **p-intake**, **x-cranes**. Approve or re-roll each against its "Accept if" list.
5. 3D: download CC0/CC-BY tuna, swordfish, shrimp (or take the kohl GLBs), and do Blender clean-up steps 1–6 + export (BLENDER_GLB_SPEC.md). Drop into `assets-src/models/`.
6. Paste `CLAUDE_PROMPT.md` into Claude Code with this folder.
**Claude**: steps 1–6 of CLAUDE_PROMPT §1 (repo, docs, issues, scaffold, CI, Vercel preview, reused media), then the Day1 issues: engine, loader, start screen + path switch, ScrubVideo, chapter config, Ocean + Pond chapters with reused clips/placeholders, HUD, rail/nav/CTA. End of day: preview link where both paths scroll end-to-end.

## Day 2
**Tarun**
1. 1080p masters for approved drafts (o-catch, p-proc, p-intake, x-cranes), then drafts → masters for **p-ponds**, **p-freeze**, **x-ship** (x-ship starts from x-cranes' last frame, so do x-cranes first).
2. Drop each master as `assets-src/video/<id>.mp4` and tell Claude which ids landed.
3. Review the Day 1 preview: comment on the PRs (Tarun merges approved PRs).
**Claude**: Day2 issues: plant chapters, documentation, port, at sea, bright globe + routes, Products with GLBs, Trust, About, Quote/RFQ + API, footer, reduced-motion, mobile, SEO. Swap in each clip as it arrives (`encode-clips.sh <id> && make-posters.sh <id>` → PR with sizes).

## Day 3
**Tarun**
1. Re-roll anything that failed review (most likely o-catch or p-proc).
2. Final GLB fixes if a model is over 1.5 MB or looks wrong.
3. Review the release preview on a laptop and a phone. Say "ship it" or list fixes.
4. After production is live and approved: attach `skylarkexim.com` in Vercel → Domains and update DNS (CLAUDE_PROMPT §11). Keep the old WordPress host until the new site is verified.
**Claude**: last clip/GLB swaps, perf pass to hit every number in §9, a11y (axe) pass, cross-browser check (Chrome, Safari macOS + iOS, Firefox, Android Chrome), Lighthouse + scroll-perf reports in the release PR, final report (CLAUDE_PROMPT §12). Production deploy only after Tarun's ok.
