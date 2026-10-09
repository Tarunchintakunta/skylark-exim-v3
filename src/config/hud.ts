// The 9 real workflow steps from skylarkexim.com (docs/CONTENT.md "Work flow"). The HUD shows step number + name + a state label.
export interface HudState {
  /** chapter progress at which this state takes over */
  at: number
  step: string
  name: string
  state?: string
  /** only at cold storage (the one temperature the site states) */
  temp?: string
}

export const COLD_STORE_TEMP = '−18 °C TO −20 °C'
