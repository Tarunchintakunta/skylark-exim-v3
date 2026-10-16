# Port sequence (#258) — plan

Four chained Higgsfield shots that become one port beat for `/story`. Branch `feat/hf-port`, PR into
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
| 4 | Shot 3's last frame | The trolley travels out over the ship and lowers the container onto the deck stack until it settles flush; the spreader unlocks and rises. | `minimax_h3` 2K, 5 s |

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

1. Stitch shots 1-4 into `masters/hf-port-FINAL.mp4` with clean cuts. Each shot starts from the previous
   shot's last frame, so straight concatenation joins them without a jump; no crossfade is needed.
2. Encode with `scripts/encode-hf.sh hf-cranes` (the #258 port clip id), master at
   `masters/hf-cranes/master.mp4`.
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
| Shot 2 clip (first attempt, discarded) | `b8d255af` | 10 |
