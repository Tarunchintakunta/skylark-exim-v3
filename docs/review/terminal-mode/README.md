# Terminal mode review material (#264)

## Recordings

| File | What it shows |
| --- | --- |
| `side-by-side-story.mp4` | Left: this build's `/story` (wild catch), warm, scrolled at a steady 26 px a frame. Right: terminal-industries.com scrolled the same way, same viewport (1280×720), same 24 fps capture. |
| `hero-sequence-scrub.mp4` | The homepage hero scrubbed through its 60-frame canvas sequence over 300 vh. |

Both were captured by Playwright at 1280×720 against the production build, the Skylark side after the warm cache had
finished, so what is on screen is what a visitor gets once a page is warm.

## 100 % crop pairs

The same region of the same frame, each file at its own pixels — no upscaling on either side.

| 1920 (what every desktop was served) | 2560 (what a retina desktop is served now) |
| --- | --- |
| `catch-net_1920.jpg` | `catch-net_2560.jpg` |
| `ponds-aerator_1920.jpg` | `ponds-aerator_2560.jpg` |
| `lab-hands_1920.jpg` | `lab-hands_2560.jpg` |
| `sail-wake_1920.jpg` | `sail-wake_2560.jpg` |

- `phone-catch_m.jpg` — the phone story crop at 100 %, out of the 810×1440 portrait clip (the master's full height, never scaled)
- `product-vannamei_960.jpg` — a product still at 100 % from its 960 export, which is its ceiling: no 4K original exists on this machine or in the repo (`docs/HD_AUDIT.md`)
