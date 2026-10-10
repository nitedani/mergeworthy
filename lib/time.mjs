export const MINUTE = 60_000
export const DAY = 24 * 60 * MINUTE

const UNITS = { '': 1, s: 1, m: 60, h: 3600 }

export function seconds(duration) {
  const m = /^(\d+(?:\.\d+)?)([smh]?)$/.exec(duration)
  return m ? Number(m[1]) * UNITS[m[2]] : NaN
}
