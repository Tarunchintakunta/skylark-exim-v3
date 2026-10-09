// Screenshot the local preview at scroll positions (used for PR screenshots).
// Usage: npm run build && npm run preview, then:
//   node scripts/shot.mjs <outdir> 1440x900 0 150vh 900vh      (y in px or vh)
// Env: HASH='#pond' · MOBILE=1 (touch + mobile UA) · RM=1 (reduced motion) · WAIT=ms after load · STEP=ms per shot
import { chromium } from '@playwright/test'
const [out, size, ...ys] = process.argv.slice(2)
const [w, h] = size.split('x').map(Number)
const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] })
const p = await b.newPage({ viewport: { width: w, height: h }, reducedMotion: process.env.RM ? 'reduce' : 'no-preference', isMobile: !!process.env.MOBILE, hasTouch: !!process.env.MOBILE })
p.on('console', m => m.type() === 'error' && console.log('console:', m.text()))
p.on('pageerror', e => console.log('pageerror:', e.message))
await p.goto('http://localhost:4173/' + (process.env.HASH || ''))
await p.waitForTimeout(+(process.env.WAIT || 1500))
for (const y of ys) {
  const px = y.endsWith('vh') ? parseFloat(y) * h / 100 : +y
  await p.evaluate(px => window.scrollTo(0, px), px)
  await p.waitForTimeout(+(process.env.STEP || 1400))
  await p.screenshot({ path: `${out}/shot-${y}.png` })
}
await b.close()
