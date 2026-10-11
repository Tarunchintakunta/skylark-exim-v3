import { readFileSync } from 'node:fs'
import type { Plugin } from 'vite'
import { exportsLine, start } from '../src/config/content'

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const css = (f: string) => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s*\n\s*/g, '')

/**
 * #207 LCP: the hero headline and body as static HTML, painted before any JS and above the loader (occluded text does
 * not count for LCP). Markup mirrors src/ui/Hero.tsx and comes from the same content.ts, so the copy never drifts.
 * The loader removes #hero-static when it finishes; React's hero sits at the same fixed position, so nothing shifts.
 */
export function staticHero(): Plugin {
  const lead = start.title.replace(/ world\.$/, '')
  const html = `<div class="hero hero--static" id="hero-static"><div class="hero__copy">
<h1 class="hero__title">${esc(lead)} <em>world</em>.</h1>
<p class="hero__body">${esc(start.body)}</p>
<div class="hero__exports"><h2 class="hero__exports-title mono">${esc(exportsLine.title)}</h2><ul>${exportsLine.items.map((t) => `<li>${esc(t)}</li>`).join('')}</ul></div>
<a class="hero__contact" href="/quote">Contact us</a><a class="hero__path" href="#pond">Or follow the ${esc(start.pond.sub.toLowerCase())} →</a>
</div></div>`
  // tokens (vars + @font-face), the base rules the hero inherits from global.css, and hero.css itself
  const base =
    'body{color:var(--ice);font-family:var(--f-body);font-size:var(--fs-body);line-height:1.6;-webkit-font-smoothing:antialiased}' +
    'h1,h2,p,ul{margin:0}ul{padding:0;list-style:none}a{color:inherit}' +
    'h1{font-family:var(--f-display);font-weight:400;letter-spacing:-0.01em;line-height:0.98;text-wrap:balance}h1 em{font-style:italic}' +
    '.mono{font-family:var(--f-body);font-size:var(--fs-small);letter-spacing:0.04em;line-height:1.45}' +
    // id selector: the bundled hero.css (.hero hidden until ready) loads after this style and must not win
    '#hero-static{visibility:visible;opacity:1;z-index:101}#hero-static .hero__copy{pointer-events:none}' +
    // short landscape phones: no room above the copy for the mark, so the loader covers it as before
    '@media (max-height:560px){#hero-static{z-index:var(--z-copy)}.loader{align-content:center;padding-top:0}}'
  return {
    name: 'static-hero',
    // 'pre': before Vite's own HTML pass, which strips CSS comments (and with them the placeholder)
    transformIndexHtml: {
      order: 'pre',
      handler: (src) =>
        src
          .replace('/*static-hero-css*/', css('styles/tokens.css') + base + css('ui/hero.css'))
          .replace('<!--static-hero-->', html),
    },
  }
}
