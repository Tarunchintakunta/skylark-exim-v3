/**
 * Simplified Skylark mark traced from the skylarkexim.com logo (leaping fish, curled shrimp, sea).
 * Stroke-only so the loader can draw it in. Replace with Tarun's vector logo when supplied (confirm-list #8).
 */
export function Mark({ className, title }: { className?: string; title?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" role={title ? 'img' : undefined} aria-hidden={title ? undefined : true} aria-label={title}>
      <path pathLength="1" d="M13 40C12 27 20 16 33 12C27 19 24 27 24 37" />
      <path pathLength="1" d="M13 40L8 45M13 40l6 3.5" />
      <path pathLength="1" d="M42 11C53 13 59 23 55 33C52 40 44 42 39 37C36 34 38 30 41 31" />
      <path pathLength="1" d="M42 11C38 8 33 7 28 8M44 17l4-3M47 23l5-2M48 29l5 0" />
      <path pathLength="1" d="M6 49Q14 44 22 49T38 49T54 48T60 47" />
      <path pathLength="1" d="M12 56Q20 52 28 56T44 56T56 55" />
    </svg>
  )
}
