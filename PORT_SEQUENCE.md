# Port sequence (#258) — plan

Six chained Higgsfield shots stitched into one port film. One of them is also the `/story` port beat. Branch `feat/hf-port`, PR into
`feat/higgsfield-story`. Never push to `main`; #193 is untouched.

## Source of truth

- Approved composition still: `docs/review/stills/258.jpg` at `1ccf00f` (PR #282).
- Grade reference: `~/Desktop/skylark-start-frames/258-port-a-4k.png`.
- Shot 1 is done and approved: `masters/hf-port-s1-clip.mp4` (2560x1440, 24 fps, 5.17 s).
- The earlier shot 2 attempt (`masters/hf-port-s2-clip.mp4`) failed its brief and is discarded.

## Shots

| Shot | Start frame | Motion | Model |
|---|---|---|---|
| 1 | `masters/hf-port-s1-start-4k-v2.png` (approved) | The truck drives through the gate onto the quay road. | done |
| 2 | New 4K `gpt_image_2_5` frame built from shot 1's last frame, truck already turned right and standing under the middle crane's spreader with the container lined up beneath it | The truck finishes the right turn and brakes to a stop with real weight and a slight suspension dip. Camera locked. | `minimax_h3` 2K, 5 s |
| 3 | Shot 2's last frame | The spreader comes down on taut cables, locks onto the container's four corners and lifts it straight up off the chassis. The truck stays still. | `minimax_h3` 2K, 5 s |
| 4a | Shot 3's last frame | The trolley travels out over the ship with the container hanging on taut cables. | `minimax_h3` 2K, 5 s |
| 4b | New 4K end frame built from shot 4a's last frame | The container is lowered onto the deck stack, settles flush, and the spreader unlocks and rises. | `minimax_h3` 2K, 5 s |
| 5 | Shot 4b's last frame | The loaded ship pulls away from the quay and heads out to open sea; the cranes stay behind it. | `minimax_h3` 2K, 5 s |

Shot 4 was first attempted as a single move (travel plus landing). The container never landed, so the move was
split into 4a (travel) and 4b (landing), each with its own start or end frame.

One generation per clip. Real-speed, weighty motion, nothing floaty.

## Rules checked on every clip

Checked on the first, middle and last frame of each clip at 100 %:

1. Right-hand-drive cab: driver and steering wheel on the vehicle's right.
2. Unbranded: no emblem, badge, lettering, number plate, container markings or signage anywhere.
3. One full-size 40 ft container, always supported — on the chassis, on cables, or on the stack. Never floating.
4. The container ship is the only vessel in the water.
5. Light-grey painted steel cranes.
6. Nothing new appears: no vehicles, boats, people or red objects.
7. No warping or morphing; rigid shapes and consistent proportions.

A failing shot is fixed once, either with a new start frame for that shot or one retake. Two failures on the
same shot, or a balance that would fall below 1500 credits, stops the run for a decision.

## Finish

1. Stitch the shots into `masters/hf-port-FINAL.mp4` with clean cuts. Each shot starts from the previous
   shot's last frame, so straight concatenation joins them without a jump; no crossfade is needed.
2. Encode with `scripts/encode-hf.sh hf-cranes` (the #258 port clip id), master at
   `masters/hf-cranes/master.mp4`.

   The full 31 s stitch cannot be the `/story` master. `FILE_CAP` is 2,300 KB per file and `BUDGET[1920]` is
   25 MB for a whole path, both fixed byte budgets with no allowance for duration, so 31 s lands at about
   590 kbit/s: mean SSIM 0.689 at 1920 against the master, where a three-second clip sits near 0.88. At a
   usable bitrate the clip alone would want roughly 14 MB at 1920, over half the path budget. So `/story`
   gets the lock-on and lift from shot 3, cut to 3.0 s, and `masters/hf-port-FINAL.mp4` stays the
   full-sequence deliverable.

   The 3.0 s length is not cosmetic. Every other clip master is exactly 3.0 s, and `solveCaps` splits each
   path's budget in proportion to clip length, so a 5.167 s port beat drew 1.72x a normal share: the other
   clips' committed files were encoded when the port beat was 3 s too, and the ocean path came to 25.67 MB
   against its 25 MB budget (`tests/weight.spec.ts`, `tests/hd.spec.ts`). At 3.0 s the share is back in line.
   This frame is also detail-dense, so its posters are encoded with `CAP_KB=230` instead of the default
   350 KB: at 350 KB the 1920 poster alone put the ocean path at 25.08 MB.
3. Micro commits on `feat/hf-port`, then a PR into `feat/higgsfield-story`.
4. Report: the final file, the PR link, and credits per shot and in total.

## Budget

Images cost 4.25 credits each, clips 10 each. Balance at the start of the run: about 2190.

## Log

| Step | Job | Credits |
|---|---|---|
| Shot 1 start frame (v1, left-hand drive, rejected) | `4396e359` | 4.25 |
| Shot 1 start frame (v2, approved) | `893ab751` | 4.25 |
| Shot 1 clip (approved) | `949bd189` | 10 |
| Shot 2 clip (first attempt, no turn and a transporter appeared, discarded) | `b8d255af` | 10 |
| Shot 2 start frame (v1, spreader stacked on the truck's container, rejected) | `15388b35` | 4.25 |
| Shot 2 start frame (v2, pass) | `b122e2cf` | 4.25 |
| Shot 2 clip (pass) | `a466c0df` | 10 |
| Shot 3 clip (pass) | `a800c4ff` | 10 |
| Shot 4 clip (single move, never lands, rejected) | `75afc09f` | 10 |
| Shot 4 end frame (container vanished, rejected) | `b29425d7` | 4.25 |
| Shot 4a clip (take 1, extra bow wash, rejected) | `b4ac390d` | 10 |
| Shot 4a clip (take 2, accepted) | `909a54c5` | 10 |
| Shot 4b end frame (pass) | `1be16c9d` | 4.25 |
| Shot 4b clip (pass) | `87a21ada` | 10 |
| Shot 5 clip (pass) | `f171f752` | 10 |
| Framing tests before the sequence (two 4K frames) | `09c77f79, b77afa65` | 8.50 |
| **Total** | | **124.00** |
