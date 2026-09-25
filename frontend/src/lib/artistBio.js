// The facts line above an artist's bio ("Formed in 1995 — Little Rock, AR").
// Pure (the translator is passed in), so it's unit-testable.

/**
 * `profile.born_or_formed` is one field for two meanings, and Apple Music
 * says which with `is_group`: a group's is when it was formed, a solo
 * artist's is when they were born. Only an explicit `false` reads as born -
 * `true`, and a profile saved before the flag existed (`null`), stay "formed".
 */
export function isSoloArtist(profile) {
  return profile?.is_group === false
}

/**
 * The line itself: when they were born/formed, then where they are from,
 * joined with a dash; `''` when the profile has neither. `t` is the i18n
 * translator (`artistBio.born` / `artistBio.formed`).
 */
export function artistFacts(profile, t) {
  const when = profile?.born_or_formed
  const label = !when
    ? ''
    : isSoloArtist(profile)
      ? t('artistBio.born', { date: when })
      : t('artistBio.formed', { year: when })
  return [label, profile?.origin].filter(Boolean).join(' — ')
}
