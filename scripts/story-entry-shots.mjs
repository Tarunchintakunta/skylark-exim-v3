// Story Entry review screenshots from the homepage (#268). node scripts/story-entry-shots.mjs <baseUrl> <outdir>
import { chromium } from '@playwright/test'
const [base = 'http://localhost:4173', out = 'docs/review/story-entry'] = process.argv.slice(2)
const b = await chromium.launch()
const SIZES = [['1440', 1440, 900, false], ['2560', 2560, 1440, false], ['390', 390, 844, true]]
for (const [name, width, height, mobile] of SIZES) {
  const ctx = await b.newContext({ viewport: { width, height }, isMobile: mobile, hasTouch: mobile })
  const p = await ctx.newPage()
  await p.goto(base)
  await p.waitForFunction(() => document.documentElement.dataset.ready === '1')
  await p.waitForSelector('#boot', { state: 'detached' })
  const section = p.locator('#story-entry')
  const grid = async () => { await section.scrollIntoViewIfNeeded(); await p.evaluate(() => document.querySelector('#story-entry').scrollIntoView()); await p.waitForTimeout(1200) }
  await grid()
  await (mobile ? p.screenshot({ path: `${out}/${name}-grid.jpg`, type: 'jpeg', quality: 86, fullPage: false }) : section.screenshot({ path: `${out}/${name}-grid.jpg`, type: 'jpeg', quality: 88 }))
  if (!mobile) {
    for (const id of ['wild', 'world']) {
      await p.locator(`[data-card="${id}"]`).hover()
      await p.waitForTimeout(1800)
      await section.screenshot({ path: `${out}/${name}-hover-${id}.jpg`, type: 'jpeg', quality: 88 })
      await p.mouse.move(2, 2)
    }
  }
  for (const id of ['wild', 'farmed', 'world']) {
    const card = p.locator(`[data-card="${id}"]`)
    await card.scrollIntoViewIfNeeded()
    await (mobile ? card.locator('.se-hit').tap() : card.locator('.se-hit').click())
    await p.waitForTimeout(2200)
    await p.screenshot({ path: `${out}/${name}-open-${id}.jpg`, type: 'jpeg', quality: 88 })
    if (mobile) {
      await card.locator('.se-widget').last().evaluate((el) => el.scrollIntoView({ block: 'end' }))
      await p.waitForTimeout(400)
      await p.screenshot({ path: `${out}/${name}-open-${id}-scrolled.jpg`, type: 'jpeg', quality: 86 })
    }
    await card.locator('.se-close').click()
    await p.waitForTimeout(1200)
  }
  await ctx.close()
}
await b.close()
