import { expect, test, type Page } from '@playwright/test'

/**
 * The film only moves forward (final audit): scrolling down plays it, scrolling up never plays a clip backwards, never
 * shows a later chapter than the one the page is on, and the top of /story is the opening's first frame, still.
 * Desktop 1440×900 (Lenis wheel) and phone 390×844 (touch emulation, native scroll), both paths.
 */
const VIEWS = {
  desktop: { viewport: { width: 1440, height: 900 }, isMobile: false, hasTouch: false },
  phone: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
} as const

type Sample = { y: number; dir: number; chapter: number; id: string | null; t: number; frame: number; shown: boolean }

/** every animation frame: the scroll, the chapter the stage shows, and the picture's own time (decoder or canvas frame) */
function record() {
  const w = window as unknown as { __fwd: Sample[]; __scrub: { id: string | null; chapter: number; shown: boolean } }
  w.__fwd = []
  let last = 0
  const loop = () => {
    const y = scrollY
    const v = [...document.querySelectorAll<HTMLVideoElement>('.stage video')].find((x) => x.style.opacity === '1')
    const c = document.querySelector<HTMLCanvasElement>('canvas.stage__seq')
    const s = w.__scrub
    w.__fwd.push({
      y,
      dir: Math.sign(y - last),
      chapter: s?.chapter ?? -1,
      id: s?.id ?? null,
      t: v && v.dataset.clip === s?.id ? v.currentTime : -1,
      frame: c && c.style.opacity === '1' ? Number(c.dataset.frame ?? -1) : -1,
      shown: !!s?.shown,
    })
    last = y
    requestAnimationFrame(loop)
  }
  requestAnimationFrame(loop)
}

const chapterOfY = (page: Page) =>
  page.evaluate(() => {
    const tops = [...document.querySelectorAll<HTMLElement>('.chapter')].map((el) => el.getBoundingClientRect().top + scrollY)
    return tops
  })

async function open(page: Page, hash = '') {
  await page.goto(`/story${hash}`)
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1' && !document.getElementById('boot'))
  await page.evaluate(record)
}

async function wheel(page: Page, dy: number, steps: number, gap: number) {
  for (let k = 0; k < steps; k++) {
    await page.mouse.wheel(0, dy)
    await page.waitForTimeout(gap)
  }
  // let Lenis settle (a jump with scrollTo while it is still easing would be overridden by its own target)
  await page.waitForFunction(() => !document.documentElement.classList.contains('lenis-scrolling'))
  await page.waitForTimeout(300)
}

/** no clip ever runs backwards while the page scrolls up, and the stage never shows a chapter below the page's own */
async function checkUpward(page: Page) {
  const tops = await chapterOfY(page)
  const s = (await page.evaluate(() => (window as unknown as { __fwd: Sample[] }).__fwd)) as Sample[]
  const chapterAt = (y: number) => tops.reduce((a, top, i) => (y >= top ? i : a), 0)
  let backwards = 0
  let later = 0
  for (let k = 1; k < s.length; k++) {
    const [a, b] = [s[k - 1], s[k]]
    if (b.chapter > chapterAt(b.y)) later++
    if (b.dir >= 0 || a.id !== b.id) continue
    if (a.t >= 0 && b.t >= 0 && b.t < a.t - 1 / 48) backwards++
    if (a.frame >= 0 && b.frame >= 0 && b.frame < a.frame) backwards++
  }
  return { backwards, later, samples: s.length }
}

for (const [name, view] of Object.entries(VIEWS)) {
  test.describe(name, () => {
    test.use(view)

    test('top of /story: the opening on its first frame, still, nothing else on screen', async ({ page }) => {
      await open(page)
      await page.waitForTimeout(2000)
      const top = await page.evaluate(() => ({
        y: scrollY,
        loop: document.querySelectorAll('.hero video').length,
        chapter: (window as unknown as { __scrub: { chapter: number } }).__scrub.chapter,
        // any decoder that shows a picture is the opening, on frame 0
        shown: [...document.querySelectorAll<HTMLVideoElement>('.stage video')].filter((v) => v.style.opacity === '1').map((v) => [v.dataset.clip, v.currentTime]),
        captions: [...document.querySelectorAll<HTMLElement>('.caption')].filter((c) => getComputedStyle(c).visibility === 'visible').length,
      }))
      expect(top.y).toBe(0)
      expect(top.loop).toBe(0)
      expect(top.chapter).toBe(0)
      for (const [id, t] of top.shown) expect([id, t]).toEqual(['opening', 0])
      expect(top.captions).toBe(0)
    })

    for (const hash of ['#ocean', '#pond'])
      test(`${hash}: fast and slow scroll down only move forward, scroll up never plays back`, async ({ page }) => {
        test.setTimeout(240_000)
        await open(page, hash)
        await page.evaluate(() => scrollTo(0, 0))
        await page.waitForTimeout(600)
        await page.evaluate(record)
        // slow down through the first chapters, then a fast run
        await wheel(page, 120, 25, 120)
        await wheel(page, 600, 12, 40)
        const down = (await page.evaluate(() => (window as unknown as { __fwd: Sample[] }).__fwd)) as Sample[]
        let back = 0
        for (let k = 1; k < down.length; k++) {
          const [a, b] = [down[k - 1], down[k]]
          if (b.chapter < a.chapter && b.dir >= 0) back++
          if (a.id === b.id && b.dir >= 0 && a.t >= 0 && b.t >= 0 && b.t < a.t - 1 / 48) back++
        }
        expect(back, 'picture went back while scrolling down').toBe(0)

        // up at every chapter: a short wheel up inside it, then on up into the one before
        const tops = await chapterOfY(page)
        for (let i = Math.min(tops.length - 2, 9); i >= 1; i--) {
          await page.evaluate(([y]) => scrollTo(0, y), [tops[i] + 300])
          await page.waitForTimeout(700)
          await page.evaluate(record)
          await wheel(page, -100, 6, 80)
          const r = await checkUpward(page)
          expect(r.backwards, `chapter ${i}: clip ran backwards`).toBe(0)
          expect(r.later, `chapter ${i}: a later chapter on screen`).toBe(0)
        }
      })

    test('refresh mid-story lands on the first frame at the top', async ({ page }) => {
      await open(page)
      await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight / 3))
      await page.waitForTimeout(800)
      await page.reload()
      await page.waitForFunction(() => document.documentElement.dataset.ready === '1')
      await page.waitForTimeout(1500)
      const s = await page.evaluate(() => ({ y: scrollY, s: (window as unknown as { __scrub: { chapter: number; target: number } }).__scrub }))
      expect(s.y).toBe(0)
      expect(s.s.chapter).toBe(0)
      expect(s.s.target).toBe(0)
    })
  })
}
