import { readFileSync } from 'node:fs'
import type { Plugin } from 'vite'
import { exportsLine, start } from '../src/config/content'

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const css = (f: string) => readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s*\n\s*/g, '')

/**
 * #207 LCP: the hero headline and body as static HTML, painted before any JS (behind the loader, which Chrome still
 * counts for LCP). Markup mirrors src/ui/Hero.tsx and comes from the same content.ts, so the copy never drifts.
 * React's Hero removes #hero-static when it takes over at ready; both sit at the same fixed position, so nothing shifts.
 */
export function staticHero(): Plugin {
  const lead = start.title.replace(/ world\.$/, '')
  const html = `<div class="hero hero--static" id="hero-static"><div class="hero__copy">
<h1 class="hero__title">${esc(lead)} <em>world</em>.</h1>
<p class="hero__body">${esc(start.body)}</p>
<div class="hero__exports"><h2 class="hero__exports-title mono">${esc(exportsLine.title)}</h2><ul>${exportsLine.items.map((t) => `<li>${esc(t)}</li>`).join('')}</ul></div>
<a class="hero__contact" href="#quote">Contact us</a><a class="hero__path" href="#pond">Or follow the ${esc(start.pond.sub.toLowerCase())} →</a>
</div></div>`
  // tokens (vars + @font-face), the base rules the hero inherits from global.css, and hero.css itself
  const base =
    'body{color:var(--ice);font-family:var(--f-body);font-size:var(--fs-body);line-height:1.6;-webkit-font-smoothing:antialiased}' +
    'h1,h2,p,ul{margin:0}ul{padding:0;list-style:none}a{color:inherit}' +
    'h1{font-family:var(--f-display);font-weight:400;letter-spacing:-0.01em;line-height:0.98;text-wrap:balance}h1 em{font-style:italic}' +
    '.mono{font-family:var(--f-body);font-size:var(--fs-small);letter-spacing:0.04em;line-height:1.45}' +
    '.hero--static{visibility:visible;opacity:1}'
  return {
    name: 'static-hero',
    transformIndexHtml: (src) =>
      src
        .replace('/*static-hero-css*/', css('styles/tokens.css') + base + css('ui/hero.css'))
        .replace('<!--static-hero-->', html),
  }
}
