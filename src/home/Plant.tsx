import { HOME, film } from '../config/content'
import { chaptersFor } from '../config/chapters'
import * as m from 'motion/react-m'
import { reveal, rise } from '../motion/tokens'

/** clip ids on the farmed-shrimp path (the plant stills) and the caption that goes with each */
const STILLS = [
  { id: 'hf-intake', copy: film.intake[0] },
  { id: 'hf-lab', copy: film.coldchain[0] },
  { id: 'hf-iqf', copy: film.coldchain[1] },
  { id: 'hf-store', copy: film.coldchain[3] },
]
const ALT = new Map(chaptersFor('pond').flatMap((c) => c.media).flatMap((m) => (m.kind === 'video' ? [[m.id, m.alt] as const] : [])))

/** The plant at Anandapuram: four first frames from the film's plant clips, each with the film's own caption (facts only). */
export function Plant() {
  return (
    <section id="plant" className="section theme-light home-plant" aria-labelledby="plant-title">
      <m.header className="section__head" {...reveal}>
        <m.p className="eyebrow mono" variants={rise}>{HOME.plant.eyebrow}</m.p>
        <m.h2 id="plant-title" className="section__title" variants={rise}>{HOME.plant.title}</m.h2>
        <m.p className="home-intro__body" variants={rise}>{HOME.plant.body}</m.p>
      </m.header>
      <m.ul className="plant-grid" {...reveal}>
        {STILLS.map(({ id, copy }) => (
          <m.li key={id} className="plant-still" variants={rise}>
            <img
              className="plant-still__img"
              src={`/media/${id}_720.webp`}
              srcSet={`/media/${id}_720.webp 720w, /media/${id}_960.webp 960w`}
              sizes="(max-width: 819px) calc(100vw - 2 * var(--gutter)), 23vw"
              width={960}
              height={540}
              alt={ALT.get(id) ?? ''}
              loading="lazy"
              decoding="async"
            />
            <p className="plant-still__eyebrow mono">{copy.eyebrow?.replace('The Plant · ', '')}</p>
            <h3 className="plant-still__title">{copy.title}</h3>
            <p className="plant-still__body">{copy.body}</p>
          </m.li>
        ))}
      </m.ul>
    </section>
  )
}
