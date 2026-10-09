# Skylark Exim v3: handoff pack

Everything Claude Code needs to build and deploy the new skylarkexim.com: a cinematic, 3D, smooth story-scroll site with two paths (THE OCEAN / THE POND) that meet at the Anandapuram plant and end on a bright globe, followed by fast Products / Why us / About / Quote sections.

**This zip contains no video and no .glb files** (it's kept small on purpose):
- Reused clips come from github.com/Tarunchintakunta/skylark; Claude's `scripts/fetch-sources.sh` copies them.
- New and regenerated clips: Tarun makes them in Higgsfield with `HIGGSFIELD_PROMPTS.md` and saves each 1080p master as `assets-src/video/<id>.mp4`.
- 3D models: Tarun makes them in Blender or downloads CC0/CC-BY models with `BLENDER_GLB_SPEC.md` and saves them as `assets-src/models/<name>.glb`.
- Claude's scripts (`scripts/`) compress all of them into `public/` within the size budgets.

## Files
| File | What it is | Who uses it |
|---|---|---|
| `CLAUDE_PROMPT.md` | The master prompt. Paste it into Claude Code. | Claude |
| `PRD.md` | Product requirements: audience, journeys, features, metrics, out of scope | Claude, Tarun |
| `TRD.md` | Technical requirements: architecture, stack versions, engines, tests, CI, deploy | Claude |
| `STORY.md` | Final scene list, copy, visual source per scene, scroll and HUD behaviour | Claude, Tarun |
| `CONTENT.md` | Every verified fact/copy block from skylarkexim.com + the "never write" list | Claude |
| `GIT_WORKFLOW.md` | Issues → branches → micro commits → small PRs; only Tarun merges | Claude |
| `HIGGSFIELD_PROMPTS.md` | 7 ready prompts (anchors, duration, camera, avoid list, accept checks, credits) | Tarun |
| `BLENDER_GLB_SPEC.md` | Model specs, free-model sources and licences, step-by-step Blender export, globe-in-code | Tarun, Claude |
| `ASSETS_SPEC.md` | Folder layout, budgets, measured encode results, how the scripts work | Claude |
| `scripts/` | `fetch-sources.sh`, `encode-clips.sh`, `make-posters.sh`, `optimize-glb.sh` (tested) | Claude |
| `templates/` | PR template and issue template for the new repo | Claude |
| `confirm-list.md` | 14 questions for Tarun, each with a safe fallback | Tarun |
| `3_DAY_PLAN.md` | Day-by-day for Tarun and Claude | both |
| `reference/` | Existing keyframes, kohl draft contact sheet, Tarun's feedback screenshots, reference-site screenshots + `REFERENCES.md` | Claude |

## Order of operations
**Tarun**
1. Answer `confirm-list.md` (optional; fallbacks exist).
2. Open Claude Code in an empty folder, put this unzipped folder in it, and paste `CLAUDE_PROMPT.md` (everything below its line). Claude creates the repo `skylark-exim-v3`, issues, and the first Vercel preview.
3. Meanwhile, generate the 7 clips (`HIGGSFIELD_PROMPTS.md`) and 3 models (`BLENDER_GLB_SPEC.md`). Put them in `assets-src/video/` and `assets-src/models/` of Claude's working copy (or send them to Claude) and say which ones arrived.
4. Review each PR's Vercel preview link; merge the ones you approve (only you merge).
5. When the release preview is right, say "ship it". Then attach `skylarkexim.com` in Vercel (DNS steps in CLAUDE_PROMPT §11).

**Claude**: follows CLAUDE_PROMPT §1 (read docs → new repo with docs → issues → scaffold → Vercel preview → reused media → features by PR), meets the numbers in §9, and reports back per §12.
