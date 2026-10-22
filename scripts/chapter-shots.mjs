// Screenshot /story chapters at a point of their scroll, at desktop and phone size (PR before/after screenshots).
//   node scripts/chapter-shots.mjs <base url> <outdir> <prefix> <path>:<chapter>:<progress> ...
//   e.g. node scripts/chapter-shots.mjs https://…vercel.app shots after pond:process:0.75 ocean:coldchain:0.25
// -> <outdir>/<prefix>-<path>-<chapter>-<progress*100>-{1440,390}.jpg   (1440x900 desktop, 390x844 phone)
import { chromium } from '@playwright/test'
const [base, out, prefix, ...specs] = process.argv.slice(2)
const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] })
for (const [w, h, mobile] of [[1440, 900, false], [390, 844, true]]) {
  for (const path of [...new Set(specs.map((s) => s.split(':')[0]))]) {
    const p = await b.newPage({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, deviceScaleFactor: mobile ? 2 : 1 })
    await p.goto(`${base}/story#${path}`, { waitUntil: 'networkidle' })
    await p.waitForTimeout(2500)
    for (const s of specs.filter((s) => s.startsWith(path + ':'))) {
      const [, id, at] = s.split(':')
      const y = await p.evaluate(([id, at]) => {
        const el = document.querySelector(`section.chapter[data-chapter="${id}"]`)
        const r = el.getBoundingClientRect()
        return scrollY + r.top + r.height * +at  // the film maps a chapter over its full height (film/controller.ts)
      }, [id, at])
      // approach from just above, as a reader scrolling down does
      await p.evaluate((y) => scrollTo(0, y - 300), y)
      await p.waitForTimeout(600)
      await p.evaluate((y) => scrollTo(0, y), y)
      await p.waitForTimeout(2500)
      await p.screenshot({ path: `${out}/${prefix}-${path}-${id}-${Math.round(+at * 100)}-${w}.jpg`, quality: 80, type: 'jpeg' })
    }
    await p.close()
  }
}
await b.close()
