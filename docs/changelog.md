---
icon: lucide/history
---

# Changelog

## [3.14.0](https://github.com/henriquesebastiao/downtify/tree/3.14.0) (2026-11-23)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.13.0...3.14.0)

**Implemented enhancements:**

- Settings switches for Artist Watch's Deezer and MusicBrainz sources [\#670](https://github.com/henriquesebastiao/downtify/issues/670)
- Prevent duplicate versions of songs already in the library \(catalog ID and song\_key guard, per-track album progress\) [\#636](https://github.com/henriquesebastiao/downtify/issues/636)
- Monitoring Button does not change state [\#631](https://github.com/henriquesebastiao/downtify/issues/631)
- Feature request: optional per-user libraries \(each user has their own, unshared library\) [\#620](https://github.com/henriquesebastiao/downtify/issues/620)
- Artist Watch can't see an artist's whole catalogue — proposal: a Lidarr-style catalogue \(Deezer now, MusicBrainz next\) [\#581](https://github.com/henriquesebastiao/downtify/issues/581)
- Allow Adding of existing tracks to imported playlist [\#550](https://github.com/henriquesebastiao/downtify/issues/550)
- Either Bug Fix or Feature Request [\#546](https://github.com/henriquesebastiao/downtify/issues/546)
- Playlists as compilation or standalone album [\#531](https://github.com/henriquesebastiao/downtify/issues/531)
- Allow clients to add/edit playlists [\#477](https://github.com/henriquesebastiao/downtify/issues/477)
- Discover section include plays from navidrome [\#423](https://github.com/henriquesebastiao/downtify/issues/423)
- For each User a Download Folder Path [\#418](https://github.com/henriquesebastiao/downtify/issues/418)
- feedbacks Downtify 3.2 [\#405](https://github.com/henriquesebastiao/downtify/issues/405)

**Fixed bugs:**

- Artist Watch: with "Keep every album complete" on, an album listed by both YouTube Music and Deezer is downloaded twice [\#669](https://github.com/henriquesebastiao/downtify/issues/669)
- \[Bug\]: Missing submit button on the Similar page prevents manual search \(v3.13.0\) [\#664](https://github.com/henriquesebastiao/downtify/issues/664)
- Artist watch saves the same audio under several tracks of an album \(official-audio swap is cached by video id only\) [\#662](https://github.com/henriquesebastiao/downtify/issues/662)
- The audio stream is unavailable [\#564](https://github.com/henriquesebastiao/downtify/issues/564)
- \(Big/Hidden \[Bug\]\) Playlist Monitor appears to download tracks that don't match personalized Spotify mixes and has been for a decent chunk of time [\#489](https://github.com/henriquesebastiao/downtify/issues/489)
- Unable to toggle off YouTube Music in Audio Sources \(Where audio comes from\) and slskd as the only source [\#471](https://github.com/henriquesebastiao/downtify/issues/471)
- Large playlist duplicated in web ui library [\#414](https://github.com/henriquesebastiao/downtify/issues/414)
- Local playlist is empty when m3u file generation is turned off [\#412](https://github.com/henriquesebastiao/downtify/issues/412)
- Slskd results are not moved into folder of playlist [\#370](https://github.com/henriquesebastiao/downtify/issues/370)

**Closed issues:**

- Large monitored playlists keep downloading songs months after they finished, with no changes on Spotify [\#573](https://github.com/henriquesebastiao/downtify/issues/573)

**Merged pull requests:**

- feat\(ui\): skeletons, lazy loading and one motion system for the SPA [\#676](https://github.com/henriquesebastiao/downtify/pull/676) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(settings\): switches for Artist Watch's Deezer and MusicBrainz [\#675](https://github.com/henriquesebastiao/downtify/pull/675) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(monitor\): download a release two catalogues list once [\#674](https://github.com/henriquesebastiao/downtify/pull/674) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(providers\): give each album track its own recording [\#673](https://github.com/henriquesebastiao/downtify/pull/673) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(mobile\): let apps delete a Library playlist [\#672](https://github.com/henriquesebastiao/downtify/pull/672) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(library\): list downloaded playlists with M3U files off [\#671](https://github.com/henriquesebastiao/downtify/pull/671) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(download\): download a playlist as one album [\#668](https://github.com/henriquesebastiao/downtify/pull/668) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(api\): let clients skip songs the library already has [\#667](https://github.com/henriquesebastiao/downtify/pull/667) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(users\): optional per-user libraries [\#666](https://github.com/henriquesebastiao/downtify/pull/666) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(similar\): let Enter submit the Similar form [\#665](https://github.com/henriquesebastiao/downtify/pull/665) ([monarchsofchaos004-gif](https://github.com/monarchsofchaos004-gif))
- feat\(upgrade\): identify songs by sound with AcoustID, opt-in [\#661](https://github.com/henriquesebastiao/downtify/pull/661) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat: notifications on Discord \(with commands\), ntfy, Gotify and webhooks [\#660](https://github.com/henriquesebastiao/downtify/pull/660) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(player\): easier seeking on the mini player's progress bar [\#659](https://github.com/henriquesebastiao/downtify/pull/659) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(aurral\): let Aurral use Downtify as a download source [\#658](https://github.com/henriquesebastiao/downtify/pull/658) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat: formats to avoid, and a Doctor section that converts them to MP3 [\#657](https://github.com/henriquesebastiao/downtify/pull/657) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(slskd\): never import another file for the one requested [\#656](https://github.com/henriquesebastiao/downtify/pull/656) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(monitor\): show each watched playlist's picture in the list [\#655](https://github.com/henriquesebastiao/downtify/pull/655) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(monitor\): keep artist watch songs a few seconds off the catalogue [\#654](https://github.com/henriquesebastiao/downtify/pull/654) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(playlists\): only warm the Spotify cache with Spotify playlist ids [\#653](https://github.com/henriquesebastiao/downtify/pull/653) ([BigBrownMF69](https://github.com/BigBrownMF69))
- ci\(smokeshow\): download coverage from fork PRs too [\#652](https://github.com/henriquesebastiao/downtify/pull/652) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(slskd\): remember failed peers, cancel transfers Downtify gave up on [\#651](https://github.com/henriquesebastiao/downtify/pull/651) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(ratings\): ride out Deezer hiccups, rest between batches, resume where it stopped [\#650](https://github.com/henriquesebastiao/downtify/pull/650) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(doctor\): show artwork on every Doctor card [\#649](https://github.com/henriquesebastiao/downtify/pull/649) ([BigBrownMF69](https://github.com/BigBrownMF69))
- ci: add coverage ci and badge to README [\#648](https://github.com/henriquesebastiao/downtify/pull/648) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(monitor\): show when an artist or playlist is already watched [\#647](https://github.com/henriquesebastiao/downtify/pull/647) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(monitor\): stop finished playlists from downloading songs again [\#646](https://github.com/henriquesebastiao/downtify/pull/646) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(playlists\): add songs the library already has to an imported pla… [\#645](https://github.com/henriquesebastiao/downtify/pull/645) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(albums\): let every album keep its own copy of a shared song [\#644](https://github.com/henriquesebastiao/downtify/pull/644) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(monitor\): warn about Spotify mixes made for one listener [\#643](https://github.com/henriquesebastiao/downtify/pull/643) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(settings\): keep slskd as the only audio source when chosen [\#642](https://github.com/henriquesebastiao/downtify/pull/642) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(slskd\): find the songs Nicotine+ finds, and keep them [\#637](https://github.com/henriquesebastiao/downtify/pull/637) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Russian language [\#526](https://github.com/henriquesebastiao/downtify/pull/526) ([MrBrillik](https://github.com/MrBrillik))

## [3.13.0](https://github.com/henriquesebastiao/downtify/tree/3.13.0) (2026-11-21)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.12.0...3.13.0)

**Merged pull requests:**

- feat\(upgrade\): ISRCs for older songs \(look up first, confident only\) [\#641](https://github.com/henriquesebastiao/downtify/pull/641) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(doctor\): the AI helper covers every Doctor section \(stacked on \#635\) [\#640](https://github.com/henriquesebastiao/downtify/pull/640) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(doctor\): Keep the selected copy sometimes fails with UNIQUE constraint on sync\_tracks.path [\#639](https://github.com/henriquesebastiao/downtify/pull/639) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(doctor\): AI helper for duplicate playlists, over MCP [\#635](https://github.com/henriquesebastiao/downtify/pull/635) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(ui\): show a "What's new" dialog on the first visit after an update [\#634](https://github.com/henriquesebastiao/downtify/pull/634) ([henriquesebastiao](https://github.com/henriquesebastiao))
- perf\(startup\): write the watch-history backfills in short batches \(45 min → seconds on big libraries\) [\#633](https://github.com/henriquesebastiao/downtify/pull/633) ([BigBrownMF69](https://github.com/BigBrownMF69))

## [3.12.0](https://github.com/henriquesebastiao/downtify/tree/3.12.0) (2026-11-20)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.11.0...3.12.0)

**Implemented enhancements:**

- A song I replaced or deleted comes back: Downtify downloads it again \(and what Doctor duplicate cleanup needs\) [\#582](https://github.com/henriquesebastiao/downtify/issues/582)
- Automatic Cookie Puller [\#569](https://github.com/henriquesebastiao/downtify/issues/569)
- Playlist Monitor sweeps \(and other queue additions\) should respect the Parallel downloads limit [\#548](https://github.com/henriquesebastiao/downtify/issues/548)

**Merged pull requests:**

- fix\(covers\): every download aims for 1200px covers from four sources [\#632](https://github.com/henriquesebastiao/downtify/pull/632) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat: backup and restore [\#630](https://github.com/henriquesebastiao/downtify/pull/630) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(monitor\): watch downloads share the Parallel downloads limit [\#629](https://github.com/henriquesebastiao/downtify/pull/629) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(covers\): option to always embed the largest cover [\#628](https://github.com/henriquesebastiao/downtify/pull/628) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(queue\): show why slskd wasn't used, and clear a watch's failures [\#627](https://github.com/henriquesebastiao/downtify/pull/627) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(slskd\): keep a shared file's own cover when it's bigger [\#626](https://github.com/henriquesebastiao/downtify/pull/626) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(settings\): say what each audio source needs [\#625](https://github.com/henriquesebastiao/downtify/pull/625) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(lyrics\): Kugou, LRCLIB search, synced-only, and "Scan and find lyrics" [\#624](https://github.com/henriquesebastiao/downtify/pull/624) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(monitor\): show announced releases and download them on release day [\#623](https://github.com/henriquesebastiao/downtify/pull/623) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(queue\): show which Monitor watch is downloading each song [\#622](https://github.com/henriquesebastiao/downtify/pull/622) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(monitor\): a click on a watch's row opens its page [\#621](https://github.com/henriquesebastiao/downtify/pull/621) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Navidrome: optionally hold library scans while someone is listening [\#619](https://github.com/henriquesebastiao/downtify/pull/619) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Doctor: fix 'Same songs' grouping; decide on each playlist group, then apply at once [\#618](https://github.com/henriquesebastiao/downtify/pull/618) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Doctor: show what's in slskd's folder next to what Downtify counts [\#617](https://github.com/henriquesebastiao/downtify/pull/617) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Monitor: find an artist by name, and warn about Spotify user links [\#616](https://github.com/henriquesebastiao/downtify/pull/616) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Covers: the minimum cover size raises the first request, and smaller cover sizes are greyed out [\#615](https://github.com/henriquesebastiao/downtify/pull/615) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Doctor: fold-out sections, playlist covers, and check again after a repair [\#614](https://github.com/henriquesebastiao/downtify/pull/614) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat\(cookies\): keep the YouTube cookies.txt signed in automatically [\#613](https://github.com/henriquesebastiao/downtify/pull/613) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(library\): never pick a replaced upload again; keep files swapped on disk [\#612](https://github.com/henriquesebastiao/downtify/pull/612) ([henriquesebastiao](https://github.com/henriquesebastiao))
- ci\(docker\): tag releases with their major and minor lines too [\#611](https://github.com/henriquesebastiao/downtify/pull/611) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [3.11.0](https://github.com/henriquesebastiao/downtify/tree/3.11.0) (2026-11-17)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.10.0...3.11.0)

**Implemented enhancements:**

- Add a karaoke view to the full-screen player [\#558](https://github.com/henriquesebastiao/downtify/issues/558)
- Permanent Delete and block action with companion Android support [\#553](https://github.com/henriquesebastiao/downtify/issues/553)

**Fixed bugs:**

- Random "ERROR: '/data/cookies.txt' does not look like a Netscape format cookies file" [\#570](https://github.com/henriquesebastiao/downtify/issues/570)
- No apparent way to close the in-app audio player [\#567](https://github.com/henriquesebastiao/downtify/issues/567)

**Closed issues:**

- Optional PostgreSQL backend: database layer, pooling and versioned migrations [\#609](https://github.com/henriquesebastiao/downtify/issues/609)
- SQLite write contention, blocking auth checks and a database-aware health check [\#608](https://github.com/henriquesebastiao/downtify/issues/608)
- Ship PostgreSQL in Docker Compose, with make targets, docs and CI [\#607](https://github.com/henriquesebastiao/downtify/issues/607)
- Migrate an existing SQLite install to PostgreSQL with a verified copy [\#606](https://github.com/henriquesebastiao/downtify/issues/606)
- Run every store and the server on SQLite or PostgreSQL [\#605](https://github.com/henriquesebastiao/downtify/issues/605)
- Minimum cover size instead of a fixed cover size [\#574](https://github.com/henriquesebastiao/downtify/issues/574)
- Doctor: repair what older Downtify versions left behind \(slskd leftovers, duplicate playlists and songs\) [\#572](https://github.com/henriquesebastiao/downtify/issues/572)

**Merged pull requests:**

- Add an optional PostgreSQL backend \(DATABASE\_URL\), with a verified SQLite migration [\#610](https://github.com/henriquesebastiao/downtify/pull/610) ([michaelmoskie](https://github.com/michaelmoskie))
- Monitor: a Wanted tab — every artist's missing releases, with Check all and Download all [\#604](https://github.com/henriquesebastiao/downtify/pull/604) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Fix: Preserve Original Cover Art When Replacing FLAC Audio [\#603](https://github.com/henriquesebastiao/downtify/pull/603) ([pakhozako](https://github.com/pakhozako))
- Monitor: change many watches at once, and check every 3 days [\#602](https://github.com/henriquesebastiao/downtify/pull/602) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Fix concurrent edits being overwritten during manual playlist maintenance [\#601](https://github.com/henriquesebastiao/downtify/pull/601) ([pakhozako](https://github.com/pakhozako))
- Fix cover thumbnail cache isolation across library directories [\#600](https://github.com/henriquesebastiao/downtify/pull/600) ([pakhozako](https://github.com/pakhozako))
- Fix stream cache cancellation and concurrency control [\#599](https://github.com/henriquesebastiao/downtify/pull/599) ([pakhozako](https://github.com/pakhozako))
- feat: Ratings from Deezer \(dztnr in Downtify\) [\#598](https://github.com/henriquesebastiao/downtify/pull/598) ([BigBrownMF69](https://github.com/BigBrownMF69))
- feat: write ISRC codes into downloads and match songs by them first [\#597](https://github.com/henriquesebastiao/downtify/pull/597) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Artist Watch: check what the library has of each release, and download what's missing [\#596](https://github.com/henriquesebastiao/downtify/pull/596) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Update French translation for 'queue' term [\#595](https://github.com/henriquesebastiao/downtify/pull/595) ([jbdesbas](https://github.com/jbdesbas))
- Fix expiration handling for pairing codes and WebSocket tickets [\#594](https://github.com/henriquesebastiao/downtify/pull/594) ([pakhozako](https://github.com/pakhozako))
- Fix podcast enclosure selection when feeds contain multiple attachments [\#593](https://github.com/henriquesebastiao/downtify/pull/593) ([pakhozako](https://github.com/pakhozako))
- Fix local M3U8 playlist discovery and maintenance [\#592](https://github.com/henriquesebastiao/downtify/pull/592) ([pakhozako](https://github.com/pakhozako))
- Fix external-library track reconciliation in hourly monitoring [\#591](https://github.com/henriquesebastiao/downtify/pull/591) ([pakhozako](https://github.com/pakhozako))
- Fix ZIP export for audio files over 2 GiB [\#590](https://github.com/henriquesebastiao/downtify/pull/590) ([pakhozako](https://github.com/pakhozako))
- Artist Watch: a catalogue of the artist's releases, with a switch per release [\#589](https://github.com/henriquesebastiao/downtify/pull/589) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Read Artist Watch discographies from MusicBrainz too [\#588](https://github.com/henriquesebastiao/downtify/pull/588) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Replace audio from a file; downloads keep hand-replaced files [\#587](https://github.com/henriquesebastiao/downtify/pull/587) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Preserve transcoded stream validators on cache hits [\#586](https://github.com/henriquesebastiao/downtify/pull/586) ([michaelmoskie](https://github.com/michaelmoskie))
- docs: complete Simplified Chinese feature translations and fix iOS links [\#585](https://github.com/henriquesebastiao/downtify/pull/585) ([pakhozako](https://github.com/pakhozako))
- Doctor: merge duplicate songs, keep both, listen before deciding [\#584](https://github.com/henriquesebastiao/downtify/pull/584) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Read Artist Watch discographies from Deezer too [\#583](https://github.com/henriquesebastiao/downtify/pull/583) ([BigBrownMF69](https://github.com/BigBrownMF69))
- fix\(player\): add a close button to the player bar [\#580](https://github.com/henriquesebastiao/downtify/pull/580) ([monarchsofchaos004-gif](https://github.com/monarchsofchaos004-gif))
- Stop Artist Watch from downloading songs the library already has [\#579](https://github.com/henriquesebastiao/downtify/pull/579) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Add CodSpeed performance benchmarks [\#578](https://github.com/henriquesebastiao/downtify/pull/578) ([codspeed[bot]](https://github.com/apps/codspeed))
- Stop concurrent downloads corrupting the shared cookies.txt [\#577](https://github.com/henriquesebastiao/downtify/pull/577) ([chiliec](https://github.com/chiliec))
- Add a minimum cover size setting [\#576](https://github.com/henriquesebastiao/downtify/pull/576) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Add a Doctor settings tab to repair what older versions left behind [\#575](https://github.com/henriquesebastiao/downtify/pull/575) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Add fine-tune quality controls for the slskd source [\#571](https://github.com/henriquesebastiao/downtify/pull/571) ([BigBrownMF69](https://github.com/BigBrownMF69))
- Keep catalog stream ETags stable across range requests [\#565](https://github.com/henriquesebastiao/downtify/pull/565) ([michaelmoskie](https://github.com/michaelmoskie))
- Search for audio when retrying downloads without a URL [\#563](https://github.com/henriquesebastiao/downtify/pull/563) ([michaelmoskie](https://github.com/michaelmoskie))
- feat-allow-metadata-modification [\#562](https://github.com/henriquesebastiao/downtify/pull/562) ([michaelmoskie](https://github.com/michaelmoskie))
- build\(deps\): bump zeroconf from 0.153.0 to 0.154.0 [\#561](https://github.com/henriquesebastiao/downtify/pull/561) ([dependabot[bot]](https://github.com/apps/dependabot))
- feat\(player\): add a karaoke view with a projected window [\#559](https://github.com/henriquesebastiao/downtify/pull/559) ([fvidals](https://github.com/fvidals))
- feat\(player\): make desktop playback controls resizable [\#557](https://github.com/henriquesebastiao/downtify/pull/557) ([michaelmoskie](https://github.com/michaelmoskie))
- Add playlist editing endpoints for connected clients [\#556](https://github.com/henriquesebastiao/downtify/pull/556) ([michaelmoskie](https://github.com/michaelmoskie))
- build\(deps\): bump docker/login-action from 4.7.0 to 4.8.0 [\#555](https://github.com/henriquesebastiao/downtify/pull/555) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add iOS App Source Link [\#549](https://github.com/henriquesebastiao/downtify/pull/549) ([michaelmoskie](https://github.com/michaelmoskie))
- Add Traditional Chinese \(zh-TW\) translation [\#545](https://github.com/henriquesebastiao/downtify/pull/545) ([monarchsofchaos004-gif](https://github.com/monarchsofchaos004-gif))

## [3.10.0](https://github.com/henriquesebastiao/downtify/tree/3.10.0) (2026-11-06)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.9.0...3.10.0)

**Implemented enhancements:**

- Native HTTP/SOCKS5 proxy support across outbound services \(optional strict mode\) [\#521](https://github.com/henriquesebastiao/downtify/issues/521)
- Feature request: Remove Soulseek source copies after successful import into the Downtify library [\#493](https://github.com/henriquesebastiao/downtify/issues/493)
- Apply the audio source order \(slskd first\) to downloads started from the search bar [\#420](https://github.com/henriquesebastiao/downtify/issues/420)
- slskd: add strict format priority and allowed-format filtering \(e.g. FLAC → 320 kbps MP3\) [\#417](https://github.com/henriquesebastiao/downtify/issues/417)
- Playlist diagnostics / health summary [\#402](https://github.com/henriquesebastiao/downtify/issues/402)
- Feature request: connect with Spotify to choose imports from user playlists [\#383](https://github.com/henriquesebastiao/downtify/issues/383)
- Feature Request: Lidarr-style Artist Library & Discography Monitoring [\#317](https://github.com/henriquesebastiao/downtify/issues/317)
- Original file format downloading option [\#249](https://github.com/henriquesebastiao/downtify/issues/249)

**Fixed bugs:**

- Title Streaming from an album can play the wrong track: `videoIdFor()` takes the first search hit and ignores duration [\#514](https://github.com/henriquesebastiao/downtify/issues/514)
- Navidrome playlist sync misses tracks unless "Report Real Path" is enabled [\#392](https://github.com/henriquesebastiao/downtify/issues/392)
- Possible race condition: slskd downloads bypass the per-target lock [\#389](https://github.com/henriquesebastiao/downtify/issues/389)
- 500 error viewing lyrics for FLAC files — ValueError in \_embedded\_lyrics [\#374](https://github.com/henriquesebastiao/downtify/issues/374)
- ValueError during library upgrade scan on .opus files with embedded lyrics [\#371](https://github.com/henriquesebastiao/downtify/issues/371)
- Every downloaded song is just called "unknown.mp3" [\#264](https://github.com/henriquesebastiao/downtify/issues/264)

**Closed issues:**

- Question: could manual playlists hold more than 500 tracks? [\#488](https://github.com/henriquesebastiao/downtify/issues/488)

**Merged pull requests:**

- Add first-interaction action [\#544](https://github.com/henriquesebastiao/downtify/pull/544) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix: improve playlist editing, Soulseek locking, and Navidrome matching [\#543](https://github.com/henriquesebastiao/downtify/pull/543) ([pakhozako](https://github.com/pakhozako))
- feat\(playlists\): reorder Library playlists and repeat songs in them [\#541](https://github.com/henriquesebastiao/downtify/pull/541) ([ruflas](https://github.com/ruflas))
- Add stale action [\#540](https://github.com/henriquesebastiao/downtify/pull/540) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(slskd\): remove source files after successful import [\#539](https://github.com/henriquesebastiao/downtify/pull/539) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(player\): reject streaming matches with wrong duration [\#538](https://github.com/henriquesebastiao/downtify/pull/538) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(lyrics\): safely read embedded lyrics across audio formats [\#537](https://github.com/henriquesebastiao/downtify/pull/537) ([pakhozako](https://github.com/pakhozako))
- docs\(i18n\): add Simplified Chinese documentation [\#536](https://github.com/henriquesebastiao/downtify/pull/536) ([pakhozako](https://github.com/pakhozako))
- feat\(proxy\): support strict outbound HTTP and SOCKS routing [\#535](https://github.com/henriquesebastiao/downtify/pull/535) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(download\): honor source order for search results [\#534](https://github.com/henriquesebastiao/downtify/pull/534) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(slskd\): add strict format priority and whitelist [\#533](https://github.com/henriquesebastiao/downtify/pull/533) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: add playlist pipeline diagnostics [\#532](https://github.com/henriquesebastiao/downtify/pull/532) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(downloads\): keep the best available original audio [\#530](https://github.com/henriquesebastiao/downtify/pull/530) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(i18n\): add Simplified Chinese \(zh-CN\) translation [\#529](https://github.com/henriquesebastiao/downtify/pull/529) ([pakhozako](https://github.com/pakhozako))

## [3.9.0](https://github.com/henriquesebastiao/downtify/tree/3.9.0) (2026-11-03)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.8.1...3.9.0)

**Implemented enhancements:**

- Add release date to library table [\#523](https://github.com/henriquesebastiao/downtify/issues/523)
- Custom cover images for my own playlists, and an optional per-user library mode with download quotas [\#520](https://github.com/henriquesebastiao/downtify/issues/520)
- \[FR\] Add OIDC authentication support [\#453](https://github.com/henriquesebastiao/downtify/issues/453)

**Merged pull requests:**

- feat\(auth\): add optional OpenID Connect login [\#527](https://github.com/henriquesebastiao/downtify/pull/527) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(playlists\): support custom playlist covers [\#525](https://github.com/henriquesebastiao/downtify/pull/525) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(library\): sort tracks by release date [\#524](https://github.com/henriquesebastiao/downtify/pull/524) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Fix queued YouTube video playback [\#522](https://github.com/henriquesebastiao/downtify/pull/522) ([michaelmoskie](https://github.com/michaelmoskie))

## [3.8.1](https://github.com/henriquesebastiao/downtify/tree/3.8.1) (2026-10-31)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.8.0...3.8.1)

**Merged pull requests:**

- perf: serve library pages without waiting on the disk [\#519](https://github.com/henriquesebastiao/downtify/pull/519) ([ruflas](https://github.com/ruflas))
- fix\(player\): keep Now playing in place at the end of the lyrics [\#518](https://github.com/henriquesebastiao/downtify/pull/518) ([ruflas](https://github.com/ruflas))
- feat\(search\): open a song result's album or artist from its row [\#517](https://github.com/henriquesebastiao/downtify/pull/517) ([michaelmcg](https://github.com/michaelmcg))
- feat\(player\): add safe playback normalization levels [\#516](https://github.com/henriquesebastiao/downtify/pull/516) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: pause server downloads and watches from settings and monitor [\#515](https://github.com/henriquesebastiao/downtify/pull/515) ([QuietForge7294](https://github.com/QuietForge7294))
- perf: reduce idle slskd polling and repeated disk scans [\#513](https://github.com/henriquesebastiao/downtify/pull/513) ([QuietForge7294](https://github.com/QuietForge7294))

## [3.8.0](https://github.com/henriquesebastiao/downtify/tree/3.8.0) (2026-10-29)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.7.0...3.8.0)

**Implemented enhancements:**

- Feature request: Add a graceful pause/resume control for the download queue [\#494](https://github.com/henriquesebastiao/downtify/issues/494)
- Feature request: Track playlist origins, activity rates, and storage usage per monitored playlist [\#492](https://github.com/henriquesebastiao/downtify/issues/492)
- Feature request: Show library storage growth and usage by audio source [\#491](https://github.com/henriquesebastiao/downtify/issues/491)
- Option to remove songs from source playlist [\#466](https://github.com/henriquesebastiao/downtify/issues/466)
- Add link to purchase music [\#429](https://github.com/henriquesebastiao/downtify/issues/429)
- Search/filter inside playlist pages [\#401](https://github.com/henriquesebastiao/downtify/issues/401)

**Fixed bugs:**

- Downtify 3.7.0 hangs on startup in Umbrel [\#498](https://github.com/henriquesebastiao/downtify/issues/498)

**Closed issues:**

- Opt-in administrator music trash with 30-day recovery [\#510](https://github.com/henriquesebastiao/downtify/issues/510)
- Optional download exclusions and cumulative attempt budgets [\#509](https://github.com/henriquesebastiao/downtify/issues/509)
- Quick watch actions from artist pages and Deezer chart playlists [\#438](https://github.com/henriquesebastiao/downtify/issues/438)

**Merged pull requests:**

- feat: add opt-in administrator music trash with 30-day recovery [\#512](https://github.com/henriquesebastiao/downtify/pull/512) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: add reversible download exclusions and cumulative attempt budgets [\#511](https://github.com/henriquesebastiao/downtify/pull/511) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: library storage and usage page \(\#491\) [\#508](https://github.com/henriquesebastiao/downtify/pull/508) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: playlist provenance and per-watch activity and storage stats \(\#492\) [\#507](https://github.com/henriquesebastiao/downtify/pull/507) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: pause and resume the download queue \(\#494\) [\#506](https://github.com/henriquesebastiao/downtify/pull/506) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Fix legacy-encoded M3U playlists breaking Library requests [\#505](https://github.com/henriquesebastiao/downtify/pull/505) ([a8h](https://github.com/a8h))
- feat: let apps sign in with a username and password [\#504](https://github.com/henriquesebastiao/downtify/pull/504) ([henriquesebastiao](https://github.com/henriquesebastiao))
- chore\(deps\): bump docker/login-action from 4.6.0 to 4.7.0 [\#503](https://github.com/henriquesebastiao/downtify/pull/503) ([dependabot[bot]](https://github.com/apps/dependabot))
- chore\(deps-dev\): bump ruff from 0.17.1 to 0.17.2 [\#502](https://github.com/henriquesebastiao/downtify/pull/502) ([dependabot[bot]](https://github.com/apps/dependabot))
- chore\(deps\): bump yt-dlp from 2026.8.19 to 2026.10.21 [\#501](https://github.com/henriquesebastiao/downtify/pull/501) ([dependabot[bot]](https://github.com/apps/dependabot))
- fix: keep monitored names readable with adjustable columns [\#500](https://github.com/henriquesebastiao/downtify/pull/500) ([QuietForge7294](https://github.com/QuietForge7294))
- fix: honor audio provider order for known YouTube videos [\#499](https://github.com/henriquesebastiao/downtify/pull/499) ([QuietForge7294](https://github.com/QuietForge7294))
- fix: validate every track of monitored artist releases [\#496](https://github.com/henriquesebastiao/downtify/pull/496) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: suggest artists from personal listening and library [\#495](https://github.com/henriquesebastiao/downtify/pull/495) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: search and filter a whole playlist from its page [\#487](https://github.com/henriquesebastiao/downtify/pull/487) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: show where to buy a song to support the artist [\#486](https://github.com/henriquesebastiao/downtify/pull/486) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: hide songs from an imported playlist and keep them out [\#485](https://github.com/henriquesebastiao/downtify/pull/485) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: add a server-wide library-only music mode [\#484](https://github.com/henriquesebastiao/downtify/pull/484) ([QuietForge7294](https://github.com/QuietForge7294))
- ci: adding an action to automatically add issues and pull requests to the Downtify project in GitHub Actions [\#481](https://github.com/henriquesebastiao/downtify/pull/481) ([henriquesebastiao](https://github.com/henriquesebastiao))
- docs: translate the documentation into every app language [\#480](https://github.com/henriquesebastiao/downtify/pull/480) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: add optional playback loudness normalization [\#479](https://github.com/henriquesebastiao/downtify/pull/479) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: save linked playlists using existing library tracks [\#478](https://github.com/henriquesebastiao/downtify/pull/478) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: import selected M3U playlists from music folders [\#476](https://github.com/henriquesebastiao/downtify/pull/476) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: collaborate on playlist tracks with named users [\#475](https://github.com/henriquesebastiao/downtify/pull/475) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: customize synchronized playlist display names [\#474](https://github.com/henriquesebastiao/downtify/pull/474) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: pin favorite playlists on the home screen [\#473](https://github.com/henriquesebastiao/downtify/pull/473) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: safely replace library recordings through Deemix [\#470](https://github.com/henriquesebastiao/downtify/pull/470) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: prefer a configured external library folder [\#469](https://github.com/henriquesebastiao/downtify/pull/469) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: add opt-in Deemix audio source [\#468](https://github.com/henriquesebastiao/downtify/pull/468) ([QuietForge7294](https://github.com/QuietForge7294))
- fix: publish upgrade lyrics across filesystem boundaries [\#440](https://github.com/henriquesebastiao/downtify/pull/440) ([QuietForge7294](https://github.com/QuietForge7294))
- feat: follow artists and Deezer chart playlists in place [\#439](https://github.com/henriquesebastiao/downtify/pull/439) ([QuietForge7294](https://github.com/QuietForge7294))
- Added support for SoundCloud, adds SoundCloud for available source [\#424](https://github.com/henriquesebastiao/downtify/pull/424) ([the1andoni](https://github.com/the1andoni))
- fix: multiples artists issues [\#411](https://github.com/henriquesebastiao/downtify/pull/411) ([fvidals](https://github.com/fvidals))

## [3.7.0](https://github.com/henriquesebastiao/downtify/tree/3.7.0) (2026-10-21)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.6.0...3.7.0)

**Implemented enhancements:**

- Feature request: share playlists with other users \(view-only\), and detach imported playlists so they can be edited [\#465](https://github.com/henriquesebastiao/downtify/issues/465)
- Explicit marker on tracks [\#431](https://github.com/henriquesebastiao/downtify/issues/431)

**Fixed bugs:**

- YouTube Music playlists are incorrectly processed as Spotify playlists \(0 tracks downloaded\) [\#460](https://github.com/henriquesebastiao/downtify/issues/460)
- Library [\#430](https://github.com/henriquesebastiao/downtify/issues/430)
- Can't sort in playlist view [\#427](https://github.com/henriquesebastiao/downtify/issues/427)
- Could not find a YouTube match for ... [\#338](https://github.com/henriquesebastiao/downtify/issues/338)

**Merged pull requests:**

- feat\(playlists\): share playlists view-only, and detach an imported playlist [\#467](https://github.com/henriquesebastiao/downtify/pull/467) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(library\): sort a playlist's songs, and a sort menu for the Tracks tab [\#464](https://github.com/henriquesebastiao/downtify/pull/464) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix: share the library with every user, and let admins hide songs from them [\#463](https://github.com/henriquesebastiao/downtify/pull/463) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: explicit marker on songs, in the file, the Library and the player [\#462](https://github.com/henriquesebastiao/downtify/pull/462) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(monitor\): YouTube Music playlists no longer hit Spotify and no longer come out empty [\#461](https://github.com/henriquesebastiao/downtify/pull/461) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(i18n\): add Korean \(ko\) translation [\#459](https://github.com/henriquesebastiao/downtify/pull/459) ([gitcodeB](https://github.com/gitcodeB))

## [3.6.0](https://github.com/henriquesebastiao/downtify/tree/3.6.0) (2026-10-20)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.5.0...3.6.0)

**Implemented enhancements:**

- implement a local music scan [\#432](https://github.com/henriquesebastiao/downtify/issues/432)

**Fixed bugs:**

- Queue tab switches back to “In Progress” while downloading [\#455](https://github.com/henriquesebastiao/downtify/issues/455)
- Library pages slow, and 500s with "OSError: \[Errno 24\]" on a large NAS library [\#445](https://github.com/henriquesebastiao/downtify/issues/445)
- slskd transfer in Completed, Rejected state waits for queued timeout instead of failing immediately [\#416](https://github.com/henriquesebastiao/downtify/issues/416)

**Closed issues:**

- Library Upgrade fails on intentionally read-only music mounts [\#443](https://github.com/henriquesebastiao/downtify/issues/443)
- Large download queues spend quadratic work reconciling reactive rows [\#441](https://github.com/henriquesebastiao/downtify/issues/441)
- Repeated artist matching stalls catalog finalization with large external libraries [\#436](https://github.com/henriquesebastiao/downtify/issues/436)
- Title match fails when the title contains " - " and the candidate has a "\(feat. …\)" suffix [\#433](https://github.com/henriquesebastiao/downtify/issues/433)

**Merged pull requests:**

- fix: stop the catalog worker again when the app shuts down [\#458](https://github.com/henriquesebastiao/downtify/pull/458) ([ruflas](https://github.com/ruflas))
- Keep the Queue tab put while a batch downloads [\#457](https://github.com/henriquesebastiao/downtify/pull/457) ([chiliec](https://github.com/chiliec))
- Add de - german translation [\#456](https://github.com/henriquesebastiao/downtify/pull/456) ([Raspi-it](https://github.com/Raspi-it))
- chore\(deps-dev\): bump ruff from 0.17.0 to 0.17.1 [\#452](https://github.com/henriquesebastiao/downtify/pull/452) ([dependabot[bot]](https://github.com/apps/dependabot))
- perf: Library grids render visible rows only and use scaled covers [\#451](https://github.com/henriquesebastiao/downtify/pull/451) ([ruflas](https://github.com/ruflas))
- perf: stop walking the library tree on playlist reads and per download [\#450](https://github.com/henriquesebastiao/downtify/pull/450) ([ruflas](https://github.com/ruflas))
- perf: cache checked sign-ins for 30 s, cleared on any revocation [\#449](https://github.com/henriquesebastiao/downtify/pull/449) ([ruflas](https://github.com/ruflas))
- perf: count served bytes in memory instead of a write per response [\#448](https://github.com/henriquesebastiao/downtify/pull/448) ([ruflas](https://github.com/ruflas))
- perf: playlist batch summaries in memory, without blocking the Library [\#447](https://github.com/henriquesebastiao/downtify/pull/447) ([ruflas](https://github.com/ruflas))
- fix: close SQLite connections when their with-block ends [\#446](https://github.com/henriquesebastiao/downtify/pull/446) ([ruflas](https://github.com/ruflas))
- fix: skip library upgrades on read-only filesystems [\#444](https://github.com/henriquesebastiao/downtify/pull/444) ([QuietForge7294](https://github.com/QuietForge7294))
- perf: reconcile reactive download queues in linear time [\#442](https://github.com/henriquesebastiao/downtify/pull/442) ([QuietForge7294](https://github.com/QuietForge7294))
- perf: keep catalog folding off the web process [\#437](https://github.com/henriquesebastiao/downtify/pull/437) ([QuietForge7294](https://github.com/QuietForge7294))
- Match titles with a dash against candidates with a feat. suffix [\#435](https://github.com/henriquesebastiao/downtify/pull/435) ([cristianchiriac](https://github.com/cristianchiriac))
- Treat rejected and timed out slskd transfers as failed [\#434](https://github.com/henriquesebastiao/downtify/pull/434) ([cristianchiriac](https://github.com/cristianchiriac))

## [3.5.0](https://github.com/henriquesebastiao/downtify/tree/3.5.0) (2026-10-14)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.4.0...3.5.0)

**Implemented enhancements:**

- Jellyfin/Plex Integration for Organized Music Libraries [\#227](https://github.com/henriquesebastiao/downtify/issues/227)

**Fixed bugs:**

- Playlist Monitor reconciliation removes valid slskd leave-in-place tracks [\#393](https://github.com/henriquesebastiao/downtify/issues/393)

**Merged pull requests:**

- chore: remove personal production compose file [\#422](https://github.com/henriquesebastiao/downtify/pull/422) ([MrBrillik](https://github.com/MrBrillik))
- chore: bump to Python 3.15, refresh dependencies, add httpx2 for tests [\#421](https://github.com/henriquesebastiao/downtify/pull/421) ([betterix](https://github.com/betterix))
- Full-track streaming and Similar tracks page [\#419](https://github.com/henriquesebastiao/downtify/pull/419) ([MrBrillik](https://github.com/MrBrillik))
- chore\(deps\): bump websockets from 17.1 to 17.2 [\#415](https://github.com/henriquesebastiao/downtify/pull/415) ([dependabot[bot]](https://github.com/apps/dependabot))
- Fix reconcile removing valid slskd leave-in-place tracks [\#413](https://github.com/henriquesebastiao/downtify/pull/413) ([chiliec](https://github.com/chiliec))
- fix: big player responsive layout [\#409](https://github.com/henriquesebastiao/downtify/pull/409) ([luizbossoi](https://github.com/luizbossoi))

## [3.4.0](https://github.com/henriquesebastiao/downtify/tree/3.4.0) (2026-10-02)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.3.0...3.4.0)

**Merged pull requests:**

- Adding local music and creating custom playlists [\#408](https://github.com/henriquesebastiao/downtify/pull/408) ([luizbossoi](https://github.com/luizbossoi))

## [3.3.0](https://github.com/henriquesebastiao/downtify/tree/3.3.0) (2026-10-01)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.2.0...3.3.0)

**Implemented enhancements:**

- feat: Expand Deezer integration \(Links, Cover Art Resolution, Finder Search & Top Charts\) [\#403](https://github.com/henriquesebastiao/downtify/issues/403)

**Merged pull requests:**

- feat: Expand Deezer integration \(Links, Cover Art Resolution, Finder Search & Top Charts\) [\#404](https://github.com/henriquesebastiao/downtify/pull/404) ([fvidals](https://github.com/fvidals))

## [3.2.0](https://github.com/henriquesebastiao/downtify/tree/3.2.0) (2026-09-28)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.1.0...3.2.0)

**Implemented enhancements:**

- Allow manual replacement of downloaded music [\#390](https://github.com/henriquesebastiao/downtify/issues/390)
- Set the following settings to be enabled by default [\#387](https://github.com/henriquesebastiao/downtify/issues/387)
- Change the web interface port via the settings menu [\#386](https://github.com/henriquesebastiao/downtify/issues/386)
- Feature request: discovery section inspired by Aurral [\#380](https://github.com/henriquesebastiao/downtify/issues/380)
- Artist Monitoring [\#379](https://github.com/henriquesebastiao/downtify/issues/379)
- Artist pages: photo, banner, bio, origin & related artists [\#376](https://github.com/henriquesebastiao/downtify/issues/376)
- refactor: some suggestions for better experience [\#375](https://github.com/henriquesebastiao/downtify/issues/375)
- feat: download top songs as a playlist [\#360](https://github.com/henriquesebastiao/downtify/issues/360)
- YouTube fallback [\#237](https://github.com/henriquesebastiao/downtify/issues/237)
- User/Password login screen [\#64](https://github.com/henriquesebastiao/downtify/issues/64)

**Fixed bugs:**

- Duplicates Queued [\#377](https://github.com/henriquesebastiao/downtify/issues/377)
- Single downloads write no album tag [\#373](https://github.com/henriquesebastiao/downtify/issues/373)

**Closed issues:**

- Add Umami Analytics to the documentation [\#396](https://github.com/henriquesebastiao/downtify/issues/396)

**Merged pull requests:**

- feat\(library\): replace a track's audio with a version picked by hand [\#400](https://github.com/henriquesebastiao/downtify/pull/400) ([henriquesebastiao](https://github.com/henriquesebastiao))
- docs: add Umami analytics to the documentation site [\#399](https://github.com/henriquesebastiao/downtify/pull/399) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(settings\): organize by artist/album, playlist covers and artist photos on by default [\#398](https://github.com/henriquesebastiao/downtify/pull/398) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: choose the server port in a new Settings \> Server section [\#397](https://github.com/henriquesebastiao/downtify/pull/397) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: user accounts - username/password sign-in, admin and user roles, per-user preferences, activity log [\#395](https://github.com/henriquesebastiao/downtify/pull/395) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(spotify\): write the album tag on single-track downloads [\#391](https://github.com/henriquesebastiao/downtify/pull/391) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(monitor\): filter artist watches by release type and new releases only [\#385](https://github.com/henriquesebastiao/downtify/pull/385) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: add Discover \(artists, albums, playlists\) and song previews on link pages [\#384](https://github.com/henriquesebastiao/downtify/pull/384) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix: support import many large playlists at once [\#382](https://github.com/henriquesebastiao/downtify/pull/382) ([wrong-commit](https://github.com/wrong-commit))
- Artist pages: photo, banner, bio, origin & related artists [\#381](https://github.com/henriquesebastiao/downtify/pull/381) ([fvidals](https://github.com/fvidals))
- feat: spotify artist discography and top songs as a playlist [\#372](https://github.com/henriquesebastiao/downtify/pull/372) ([fvidals](https://github.com/fvidals))

## [3.1.0](https://github.com/henriquesebastiao/downtify/tree/3.1.0) (2026-09-21)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/3.0.0...3.1.0)

**Implemented enhancements:**

- Add "{year}" as file naming tag/variable [\#366](https://github.com/henriquesebastiao/downtify/issues/366)
- Add support for podcasts [\#347](https://github.com/henriquesebastiao/downtify/issues/347)

**Fixed bugs:**

- \[error?\] The page needs to be reloaded. [\#368](https://github.com/henriquesebastiao/downtify/issues/368)
- PWA on Android Chrome, This App Cannot Be Installed, accessing via Tailscale url [\#367](https://github.com/henriquesebastiao/downtify/issues/367)
- 2.13.0-rc.1: downloads fail with cookies set, node JS runtime is never enabled [\#362](https://github.com/henriquesebastiao/downtify/issues/362)

**Merged pull requests:**

- feat\(podcasts\): subscribe to shows, download episodes, remember where you left off [\#369](https://github.com/henriquesebastiao/downtify/pull/369) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix: restore deno as JS runtime for yt-dlp \(fixes \#362\) [\#365](https://github.com/henriquesebastiao/downtify/pull/365) ([betterix](https://github.com/betterix))

## [3.0.0](https://github.com/henriquesebastiao/downtify/tree/3.0.0) (2026-09-19)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.13.0-rc.1...3.0.0)

**Implemented enhancements:**

- Add the ability to like songs [\#363](https://github.com/henriquesebastiao/downtify/issues/363)
- Implement an equalizer for the built-in player [\#358](https://github.com/henriquesebastiao/downtify/issues/358)
- Lyrics Provider Fallback / Priority Order Configuratino [\#354](https://github.com/henriquesebastiao/downtify/issues/354)
- Repair / Refresh Existing Library Metadata Without Redownloading Audio [\#353](https://github.com/henriquesebastiao/downtify/issues/353)
- Trigger Navidrome Playlist Refresh After Monitored Playlist Updates [\#352](https://github.com/henriquesebastiao/downtify/issues/352)
- Save monitored playlist cover artwork alongside generated M3U playlists [\#351](https://github.com/henriquesebastiao/downtify/issues/351)
- Add library upgrade/repair option using slskd for better files and higher-resolution artwork [\#350](https://github.com/henriquesebastiao/downtify/issues/350)
- Separate Playlist Watch and Artist Watch into organized sections/tabs/page [\#349](https://github.com/henriquesebastiao/downtify/issues/349)

**Fixed bugs:**

- Library --\> Filter By \(dropdown\) broken/leaks accross windows/tiling/monitor [\#348](https://github.com/henriquesebastiao/downtify/issues/348)

**Merged pull requests:**

- Downtify v3 [\#359](https://github.com/henriquesebastiao/downtify/pull/359) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: download playlist cover art [\#356](https://github.com/henriquesebastiao/downtify/pull/356) ([fvidals](https://github.com/fvidals))

## [2.13.0-rc.1](https://github.com/henriquesebastiao/downtify/tree/2.13.0-rc.1) (2026-09-16)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.12.0...2.13.0-rc.1)

**Implemented enhancements:**

- 'Download All' button on Library page [\#344](https://github.com/henriquesebastiao/downtify/issues/344)
- connect slskd to Downtify [\#174](https://github.com/henriquesebastiao/downtify/issues/174)

**Fixed bugs:**

- M4A/Quality Issue [\#281](https://github.com/henriquesebastiao/downtify/issues/281)
- Year tag not written: enrich\_from\_match discards the album year that get\_album already returns [\#235](https://github.com/henriquesebastiao/downtify/issues/235)

**Merged pull requests:**

- feat\(library\): download selected tracks as one ZIP [\#345](https://github.com/henriquesebastiao/downtify/pull/345) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Replace deno with nodejs runtime; migrate FastAPI startup to lifespan handler [\#343](https://github.com/henriquesebastiao/downtify/pull/343) ([betterix](https://github.com/betterix))
- perf: parallelize downloads, metadata lookups, Spotify paging and library tag reads [\#342](https://github.com/henriquesebastiao/downtify/pull/342) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(download\): honor the chosen bitrate for M4A/OPUS, fix OGG conversion crash [\#341](https://github.com/henriquesebastiao/downtify/pull/341) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(player\): hide the volume slider on mobile, keep audio at full volume [\#340](https://github.com/henriquesebastiao/downtify/pull/340) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Backfill track year from the resolved YT Music album [\#339](https://github.com/henriquesebastiao/downtify/pull/339) ([jusseppe88](https://github.com/jusseppe88))
- Add slskd provider, Navidrome playlist sync, library paths, and queue UX [\#182](https://github.com/henriquesebastiao/downtify/pull/182) ([dx616b](https://github.com/dx616b))

## [2.12.0](https://github.com/henriquesebastiao/downtify/tree/2.12.0) (2026-09-13)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.11.0...2.12.0)

**Implemented enhancements:**

- Replace icons with Font Awesome [\#333](https://github.com/henriquesebastiao/downtify/issues/333)
- Replace `requests` with `httpx` [\#330](https://github.com/henriquesebastiao/downtify/issues/330)
- Improved page number display when pagination is present [\#328](https://github.com/henriquesebastiao/downtify/issues/328)
- Enable the selection of tracks for mass deletion via the Library menu [\#326](https://github.com/henriquesebastiao/downtify/issues/326)
- Add a notification for the user that a new version of Downtify is available [\#325](https://github.com/henriquesebastiao/downtify/issues/325)
- PWA \(progressive web app\) Icon [\#324](https://github.com/henriquesebastiao/downtify/issues/324)
- paste cookies file via web interface [\#280](https://github.com/henriquesebastiao/downtify/issues/280)

**Fixed bugs:**

- Delete lyrics when the music file is deleted from the library [\#319](https://github.com/henriquesebastiao/downtify/issues/319)
- Downtify v2.10.2 cannot download: yt-dlp cookies issue [\#308](https://github.com/henriquesebastiao/downtify/issues/308)
- OS error: file name too long [\#268](https://github.com/henriquesebastiao/downtify/issues/268)
- Adjust CSS con mobile [\#228](https://github.com/henriquesebastiao/downtify/issues/228)
- youtube bot detection error [\#225](https://github.com/henriquesebastiao/downtify/issues/225)
- Song age restricted even with cookies linked [\#203](https://github.com/henriquesebastiao/downtify/issues/203)

**Merged pull requests:**

- fix\(match\): accept Spotify "- Ao Vivo" titles, fall back to standard YouTube [\#337](https://github.com/henriquesebastiao/downtify/pull/337) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(player\): global mini player bar [\#336](https://github.com/henriquesebastiao/downtify/pull/336) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(player\): stop the now-playing widget from resizing/scrolling on a long name, fix playlist folder leaking into artist [\#335](https://github.com/henriquesebastiao/downtify/pull/335) ([henriquesebastiao](https://github.com/henriquesebastiao))
- refactor\(ui\): replace all Clarity icons with Font Awesome [\#334](https://github.com/henriquesebastiao/downtify/pull/334) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(ui\): condense pagination to a fixed number of pages, not all of them [\#332](https://github.com/henriquesebastiao/downtify/pull/332) ([henriquesebastiao](https://github.com/henriquesebastiao))
- core: Replacing requests with httpx [\#331](https://github.com/henriquesebastiao/downtify/pull/331) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(update-check\): notify when a newer Downtify version is out [\#329](https://github.com/henriquesebastiao/downtify/pull/329) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(library\): select and bulk-delete tracks, including across pages [\#327](https://github.com/henriquesebastiao/downtify/pull/327) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(library\): clean up sidecars and empty folders when deleting a track [\#323](https://github.com/henriquesebastiao/downtify/pull/323) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat\(cookies\): upload a YouTube cookies.txt from the settings UI [\#320](https://github.com/henriquesebastiao/downtify/pull/320) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [2.11.0](https://github.com/henriquesebastiao/downtify/tree/2.11.0) (2026-09-11)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.10.2...2.11.0)

**Implemented enhancements:**

- \[Feature Request\] Download using spotify [\#287](https://github.com/henriquesebastiao/downtify/issues/287)
- Save downloaded songs in database instead of checking destination folder [\#283](https://github.com/henriquesebastiao/downtify/issues/283)
- \[Feature Request\] Allow Grouping by Playlist/Artist/Album in Library and Player screens [\#277](https://github.com/henriquesebastiao/downtify/issues/277)
- "display": "standalone" to web manifest for iOS PWA support [\#270](https://github.com/henriquesebastiao/downtify/issues/270)
- Youtube Playlist Download [\#269](https://github.com/henriquesebastiao/downtify/issues/269)
- Disable overwrite option [\#267](https://github.com/henriquesebastiao/downtify/issues/267)
- Disable Artwork Downloading [\#263](https://github.com/henriquesebastiao/downtify/issues/263)
- Play songs by playlist [\#259](https://github.com/henriquesebastiao/downtify/issues/259)
- health check [\#258](https://github.com/henriquesebastiao/downtify/issues/258)
- Artist Watch Feature [\#253](https://github.com/henriquesebastiao/downtify/issues/253)
- File Format Token - Track number [\#251](https://github.com/henriquesebastiao/downtify/issues/251)
- Create M3U immediately [\#238](https://github.com/henriquesebastiao/downtify/issues/238)
- Download all queue [\#224](https://github.com/henriquesebastiao/downtify/issues/224)
- Cluster download by album as well as artist? [\#218](https://github.com/henriquesebastiao/downtify/issues/218)
- Ability to download from CSV [\#204](https://github.com/henriquesebastiao/downtify/issues/204)
- Add a configurable delay/sleep interval between song downloads [\#201](https://github.com/henriquesebastiao/downtify/issues/201)
- \[Feature Request\] Artist search/download [\#199](https://github.com/henriquesebastiao/downtify/issues/199)
- Add Sync Time Ability [\#192](https://github.com/henriquesebastiao/downtify/issues/192)
- Playlist Monitor - sorting [\#186](https://github.com/henriquesebastiao/downtify/issues/186)
- Enable a greater number of simultaneous downloads for faster internet connections [\#175](https://github.com/henriquesebastiao/downtify/issues/175)

**Fixed bugs:**

- Scrollbar jumping out of widgets [\#312](https://github.com/henriquesebastiao/downtify/issues/312)
- Playlist watch [\#257](https://github.com/henriquesebastiao/downtify/issues/257)

**Closed issues:**

- Security: request to enable private vulnerability reporting [\#276](https://github.com/henriquesebastiao/downtify/issues/276)

**Merged pull requests:**

- feat\(pwa\): installable web app manifest + iOS/Android home-screen support [\#316](https://github.com/henriquesebastiao/downtify/pull/316) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix\(monitor\): trust the downloaded-tracks DB, not the filesystem [\#315](https://github.com/henriquesebastiao/downtify/pull/315) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: filter by playlist, artist or album \(same as player\) [\#314](https://github.com/henriquesebastiao/downtify/pull/314) ([henriquesebastiao](https://github.com/henriquesebastiao))
- style: Fix scrollbar poking past rounded corners [\#313](https://github.com/henriquesebastiao/downtify/pull/313) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Strengthen glass effect on top nav bar [\#311](https://github.com/henriquesebastiao/downtify/pull/311) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Bulgarian translation [\#310](https://github.com/henriquesebastiao/downtify/pull/310) ([alex-kirkata](https://github.com/alex-kirkata))
- fix: resolve vulnerabilities and update Docker runtime [\#309](https://github.com/henriquesebastiao/downtify/pull/309) ([betterix](https://github.com/betterix))
- feat: Download and monitor YouTube Music playlists and @handle artists [\#307](https://github.com/henriquesebastiao/downtify/pull/307) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add an option to skip songs already downloaded anywhere in the … [\#305](https://github.com/henriquesebastiao/downtify/pull/305) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add cover art resolution and a way to skip it entirely [\#304](https://github.com/henriquesebastiao/downtify/pull/304) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Let the Built-in Player play a single downloaded playlist [\#303](https://github.com/henriquesebastiao/downtify/pull/303) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add a built-in Docker HEALTHCHECK, toggleable via DOWNTIFY\_HEAL… [\#302](https://github.com/henriquesebastiao/downtify/pull/302) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add Artist Watch to the Playlist Monitor [\#301](https://github.com/henriquesebastiao/downtify/pull/301) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add {tracknumber} filename template token [\#300](https://github.com/henriquesebastiao/downtify/pull/300) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Feature/incremental m3u monitor [\#299](https://github.com/henriquesebastiao/downtify/pull/299) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Add CSV library import \(Soundiiz, TuneMyMusic, Exportify\) [\#297](https://github.com/henriquesebastiao/downtify/pull/297) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Add configurable delay between song downloads [\#296](https://github.com/henriquesebastiao/downtify/pull/296) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add DOWNTIFY\_MONITOR\_SYNC\_TIME to anchor daily+ playlist syncs [\#295](https://github.com/henriquesebastiao/downtify/pull/295) ([henriquesebastiao](https://github.com/henriquesebastiao))
- feat: Add sorting to Playlist Monitor page [\#294](https://github.com/henriquesebastiao/downtify/pull/294) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Add custom parallel downloads \(1-30\) to Settings [\#293](https://github.com/henriquesebastiao/downtify/pull/293) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [2.10.2](https://github.com/henriquesebastiao/downtify/tree/2.10.2) (2026-09-09)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.10.1...2.10.2)

**Implemented enhancements:**

- Delete untracked songs [\#185](https://github.com/henriquesebastiao/downtify/issues/185)

**Fixed bugs:**

- Downtify 2.9.1 fails to download YouTube Music [\#247](https://github.com/henriquesebastiao/downtify/issues/247)

**Merged pull requests:**

- core: Update packages \(2026-9-8\) [\#290](https://github.com/henriquesebastiao/downtify/pull/290) ([henriquesebastiao](https://github.com/henriquesebastiao))
- fix: enable yt-dlp's remote EJS component for YouTube SABR fallback [\#286](https://github.com/henriquesebastiao/downtify/pull/286) ([Athos97](https://github.com/Athos97))
- fix: save MP3 tags as ID3v2.4 instead of v2.3 [\#285](https://github.com/henriquesebastiao/downtify/pull/285) ([Athos97](https://github.com/Athos97))
- added hungarian translation [\#284](https://github.com/henriquesebastiao/downtify/pull/284) ([betterix](https://github.com/betterix))

## [2.10.1](https://github.com/henriquesebastiao/downtify/tree/2.10.1) (2026-08-12)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.10.0...2.10.1)

**Implemented enhancements:**

- saving a song with an album name [\#173](https://github.com/henriquesebastiao/downtify/issues/173)
- Output Structure [\#144](https://github.com/henriquesebastiao/downtify/issues/144)
- Support for reverse proxy with Cloudflare Tunnel \(ROOT\_URL / BASE\_URL env support\) [\#49](https://github.com/henriquesebastiao/downtify/issues/49)

**Fixed bugs:**

- Age restricted content having issues with cookies, or wanting age approval [\#183](https://github.com/henriquesebastiao/downtify/issues/183)
- Cookies issues [\#160](https://github.com/henriquesebastiao/downtify/issues/160)

**Merged pull requests:**

- Remove dist folder [\#256](https://github.com/henriquesebastiao/downtify/pull/256) ([fracarma](https://github.com/fracarma))
- build\(deps\): Bump docker/login-action from 4.5.2 to 4.6.0 [\#255](https://github.com/henriquesebastiao/downtify/pull/255) ([dependabot[bot]](https://github.com/apps/dependabot))

## [2.10.0](https://github.com/henriquesebastiao/downtify/tree/2.10.0) (2026-08-11)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.9.2...2.10.0)

**Implemented enhancements:**

- Youtube album download [\#244](https://github.com/henriquesebastiao/downtify/pull/244) ([fracarma](https://github.com/fracarma))

## [2.9.2](https://github.com/henriquesebastiao/downtify/tree/2.9.2) (2026-08-11)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.9.1...2.9.2)

**Fixed bugs:**

- Downtify grabbing the wrong audio [\#159](https://github.com/henriquesebastiao/downtify/issues/159)

**Merged pull requests:**

- build\(deps-dev\): Bump zensical from 0.0.52 to 0.0.53 [\#252](https://github.com/henriquesebastiao/downtify/pull/252) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump docker/login-action from 4 to 4.5.2 [\#248](https://github.com/henriquesebastiao/downtify/pull/248) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add Turkish Locale Support [\#245](https://github.com/henriquesebastiao/downtify/pull/245) ([Singulariity](https://github.com/Singulariity))
- build\(deps\): Bump actions/labeler from 6 to 7 [\#242](https://github.com/henriquesebastiao/downtify/pull/242) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump zensical from 0.0.50 to 0.0.51 [\#241](https://github.com/henriquesebastiao/downtify/pull/241) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump websockets from 16.1 to 16.1.1 [\#240](https://github.com/henriquesebastiao/downtify/pull/240) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump actions/setup-python from 6 to 7 [\#239](https://github.com/henriquesebastiao/downtify/pull/239) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump ruff from 0.15.21 to 0.15.22 [\#236](https://github.com/henriquesebastiao/downtify/pull/236) ([dependabot[bot]](https://github.com/apps/dependabot))
- Check the album and song names [\#234](https://github.com/henriquesebastiao/downtify/pull/234) ([fracarma](https://github.com/fracarma))

## [2.9.1](https://github.com/henriquesebastiao/downtify/tree/2.9.1) (2026-07-16)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.9.0...2.9.1)

**Fixed bugs:**

- Recognize playlist links copied from Spotify interfaces in other languages [\#230](https://github.com/henriquesebastiao/downtify/issues/230)

**Merged pull requests:**

- Recognize Spotify URLs with locale segment \(intl-xx\) [\#233](https://github.com/henriquesebastiao/downtify/pull/233) ([mozuvic1](https://github.com/mozuvic1))
- build\(deps\): Bump actions/setup-node from 6 to 7 [\#232](https://github.com/henriquesebastiao/downtify/pull/232) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump node from 20-alpine to 26-alpine [\#231](https://github.com/henriquesebastiao/downtify/pull/231) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add option to separate songs by album [\#229](https://github.com/henriquesebastiao/downtify/pull/229) ([fracarma](https://github.com/fracarma))

## [2.9.0](https://github.com/henriquesebastiao/downtify/tree/2.9.0) (2026-07-12)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.8.0...2.9.0)

**Fixed bugs:**

- Various Artists [\#207](https://github.com/henriquesebastiao/downtify/issues/207)
- Renaming not working [\#194](https://github.com/henriquesebastiao/downtify/issues/194)
- OPUS music have no cover art [\#165](https://github.com/henriquesebastiao/downtify/issues/165)

**Merged pull requests:**

- Fix output filename subpaths [\#226](https://github.com/henriquesebastiao/downtify/pull/226) ([FidelGB](https://github.com/FidelGB))
- Fix OPUS format missing cover art [\#217](https://github.com/henriquesebastiao/downtify/pull/217) ([berkeozgen08](https://github.com/berkeozgen08))
- build\(deps-dev\): Bump ruff from 0.15.18 to 0.15.20 [\#214](https://github.com/henriquesebastiao/downtify/pull/214) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump mutagen from 1.47.0 to 1.48.1 [\#213](https://github.com/henriquesebastiao/downtify/pull/213) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump zensical from 0.0.45 to 0.0.46 [\#209](https://github.com/henriquesebastiao/downtify/pull/209) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add Various Artists in album Artist if there are more than one artists [\#208](https://github.com/henriquesebastiao/downtify/pull/208) ([Robokishan](https://github.com/Robokishan))
- build\(deps\): Bump actions/checkout from 6 to 7 [\#206](https://github.com/henriquesebastiao/downtify/pull/206) ([dependabot[bot]](https://github.com/apps/dependabot))
- Use the ID3v2.4 separator for artists: "; " [\#205](https://github.com/henriquesebastiao/downtify/pull/205) ([fracarma](https://github.com/fracarma))
- feat: add Greek translation  [\#197](https://github.com/henriquesebastiao/downtify/pull/197) ([Harrygr-droid](https://github.com/Harrygr-droid))
- build\(deps-dev\): Bump zensical from 0.0.44 to 0.0.45 [\#196](https://github.com/henriquesebastiao/downtify/pull/196) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump yt-dlp from 2026.3.17 to 2026.6.9 [\#195](https://github.com/henriquesebastiao/downtify/pull/195) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump ytmusicapi from 1.12.0 to 1.12.1 [\#193](https://github.com/henriquesebastiao/downtify/pull/193) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump zensical from 0.0.43 to 0.0.44 [\#190](https://github.com/henriquesebastiao/downtify/pull/190) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump uvicorn from 0.48.0 to 0.49.0 [\#189](https://github.com/henriquesebastiao/downtify/pull/189) ([dependabot[bot]](https://github.com/apps/dependabot))

## [2.8.0](https://github.com/henriquesebastiao/downtify/tree/2.8.0) (2026-06-02)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.7.0...2.8.0)

**Security fixes:**

- vulnerabilities [\#170](https://github.com/henriquesebastiao/downtify/issues/170)

**Merged pull requests:**

- build\(deps-dev\): Bump codeflash from 0.20.5 to 0.20.6 [\#188](https://github.com/henriquesebastiao/downtify/pull/188) ([dependabot[bot]](https://github.com/apps/dependabot))
- feat: enrich audio tags with genre from public iTunes Search API [\#187](https://github.com/henriquesebastiao/downtify/pull/187) ([Ramss3s](https://github.com/Ramss3s))
- build\(deps-dev\): Bump ruff from 0.15.14 to 0.15.15 [\#184](https://github.com/henriquesebastiao/downtify/pull/184) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump uvicorn from 0.47.0 to 0.48.0 [\#181](https://github.com/henriquesebastiao/downtify/pull/181) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump actions/checkout from 4 to 6 [\#180](https://github.com/henriquesebastiao/downtify/pull/180) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump astral-sh/setup-uv from 6 to 7 [\#179](https://github.com/henriquesebastiao/downtify/pull/179) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add CodeFlash GitHub Actions workflow [\#178](https://github.com/henriquesebastiao/downtify/pull/178) ([codeflash-ai[bot]](https://github.com/apps/codeflash-ai))
- core: Update dependencies [\#177](https://github.com/henriquesebastiao/downtify/pull/177) ([henriquesebastiao](https://github.com/henriquesebastiao))
- build\(deps-dev\): Bump zensical from 0.0.41 to 0.0.43 [\#176](https://github.com/henriquesebastiao/downtify/pull/176) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump uvicorn from 0.46.0 to 0.47.0 [\#169](https://github.com/henriquesebastiao/downtify/pull/169) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump requests from 2.34.0 to 2.34.1 [\#166](https://github.com/henriquesebastiao/downtify/pull/166) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump requests from 2.33.1 to 2.34.0 [\#164](https://github.com/henriquesebastiao/downtify/pull/164) ([dependabot[bot]](https://github.com/apps/dependabot))

## [2.7.0](https://github.com/henriquesebastiao/downtify/tree/2.7.0) (2026-05-11)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.6.1...2.7.0)

**Implemented enhancements:**

- Configurable Parallel Downloads [\#158](https://github.com/henriquesebastiao/downtify/issues/158)
- Allow Weekly or Monthly Playlist Synchronization [\#157](https://github.com/henriquesebastiao/downtify/issues/157)

**Merged pull requests:**

- Add new time intervals for weekly and monthly options [\#163](https://github.com/henriquesebastiao/downtify/pull/163) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Add parallel downloads feature and enhance settings [\#162](https://github.com/henriquesebastiao/downtify/pull/162) ([henriquesebastiao](https://github.com/henriquesebastiao))
- build\(deps-dev\): Bump zensical from 0.0.40 to 0.0.41 [\#161](https://github.com/henriquesebastiao/downtify/pull/161) ([dependabot[bot]](https://github.com/apps/dependabot))

## [2.6.1](https://github.com/henriquesebastiao/downtify/tree/2.6.1) (2026-05-05)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.6.0...2.6.1)

**Merged pull requests:**

- Retrieve Artist, Track Number and Year when retrieving an album [\#156](https://github.com/henriquesebastiao/downtify/pull/156) ([fracarma](https://github.com/fracarma))
- build\(deps-dev\): Bump zensical from 0.0.39 to 0.0.40 [\#155](https://github.com/henriquesebastiao/downtify/pull/155) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump actions/labeler from 5 to 6 [\#153](https://github.com/henriquesebastiao/downtify/pull/153) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add documentation [\#152](https://github.com/henriquesebastiao/downtify/pull/152) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [2.6.0](https://github.com/henriquesebastiao/downtify/tree/2.6.0) (2026-05-03)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.5.0...2.6.0)

**Implemented enhancements:**

- Disable lyric download [\#145](https://github.com/henriquesebastiao/downtify/issues/145)
- Adding functionality to save music into folders by artist [\#151](https://github.com/henriquesebastiao/downtify/pull/151) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Fixing download history clearing [\#150](https://github.com/henriquesebastiao/downtify/pull/150) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Adding functionality to disable lyrics downloads [\#148](https://github.com/henriquesebastiao/downtify/pull/148) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Fixed bugs:**

- Download History Persisting After Clearing [\#146](https://github.com/henriquesebastiao/downtify/issues/146)
- Settings Not Persisting [\#142](https://github.com/henriquesebastiao/downtify/issues/142)

## [2.5.0](https://github.com/henriquesebastiao/downtify/tree/2.5.0) (2026-05-02)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.4.3...2.5.0)

**Implemented enhancements:**

- Support for Large Playlists [\#128](https://github.com/henriquesebastiao/downtify/issues/128)
- Allowing downloads of playlists with over 100 songs [\#147](https://github.com/henriquesebastiao/downtify/pull/147) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [2.4.3](https://github.com/henriquesebastiao/downtify/tree/2.4.3) (2026-04-30)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.4.2...2.4.3)

**Implemented enhancements:**

- Persisting settings in memory [\#143](https://github.com/henriquesebastiao/downtify/pull/143) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [2.4.2](https://github.com/henriquesebastiao/downtify/tree/2.4.2) (2026-04-30)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.4.1...2.4.2)

**Implemented enhancements:**

- Improving logs with loguru [\#141](https://github.com/henriquesebastiao/downtify/pull/141) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [2.4.1](https://github.com/henriquesebastiao/downtify/tree/2.4.1) (2026-04-29)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.4.0...2.4.1)

**Implemented enhancements:**

- db in download folder is not a good idea [\#139](https://github.com/henriquesebastiao/downtify/issues/139)
- Creating a separate directory to save the SQLite database [\#140](https://github.com/henriquesebastiao/downtify/pull/140) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Merged pull requests:**

- build\(deps\): Bump docker/login-action from 3 to 4 [\#138](https://github.com/henriquesebastiao/downtify/pull/138) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump docker/metadata-action from 5 to 6 [\#137](https://github.com/henriquesebastiao/downtify/pull/137) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump docker/build-push-action from 6 to 7 [\#136](https://github.com/henriquesebastiao/downtify/pull/136) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump docker/setup-buildx-action from 3 to 4 [\#135](https://github.com/henriquesebastiao/downtify/pull/135) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump docker/setup-qemu-action from 3 to 4 [\#134](https://github.com/henriquesebastiao/downtify/pull/134) ([dependabot[bot]](https://github.com/apps/dependabot))

## [2.4.0](https://github.com/henriquesebastiao/downtify/tree/2.4.0) (2026-04-29)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.3.0...2.4.0)

## [2.3.0](https://github.com/henriquesebastiao/downtify/tree/2.3.0) (2026-04-28)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.2.0...2.3.0)

**Implemented enhancements:**

- feat: Settings toggle for M3U + Playlist Monitor integration [\#127](https://github.com/henriquesebastiao/downtify/pull/127) ([gmontard](https://github.com/gmontard))

**Closed issues:**

- Refuses to read config file on ZimaOS [\#123](https://github.com/henriquesebastiao/downtify/issues/123)
- I wasted an hour trying to make Docker to work, why couldn't this be an EXE file? [\#107](https://github.com/henriquesebastiao/downtify/issues/107)

## [2.2.0](https://github.com/henriquesebastiao/downtify/tree/2.2.0) (2026-04-28)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.1.1...2.2.0)

**Implemented enhancements:**

- feat: Generate M3U playlist files for Spotify playlists [\#126](https://github.com/henriquesebastiao/downtify/pull/126) ([gmontard](https://github.com/gmontard))

## [2.1.1](https://github.com/henriquesebastiao/downtify/tree/2.1.1) (2026-04-28)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.1.0...2.1.1)

**Fixed bugs:**

- Album Details Missing in Metadata [\#125](https://github.com/henriquesebastiao/downtify/issues/125)

## [2.1.0](https://github.com/henriquesebastiao/downtify/tree/2.1.0) (2026-04-28)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/2.0.0...2.1.0)

**Implemented enhancements:**

- Feature: set output file bitrate [\#63](https://github.com/henriquesebastiao/downtify/issues/63)
- Feature: Spotify Playlist Change Detection and Sync [\#47](https://github.com/henriquesebastiao/downtify/issues/47)
- feature request: lyric provider [\#31](https://github.com/henriquesebastiao/downtify/issues/31)
- Implementing downloads without relying on Spotify credentials brings many improvements [\#124](https://github.com/henriquesebastiao/downtify/pull/124) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Fixed bugs:**

- Spotify direct link to a music or to a playlist gives wrong results [\#104](https://github.com/henriquesebastiao/downtify/issues/104)

**Closed issues:**

- Error in ratelimit [\#117](https://github.com/henriquesebastiao/downtify/issues/117)
- No downloads are queued. Search for a song to begin. [\#106](https://github.com/henriquesebastiao/downtify/issues/106)

## [2.0.0](https://github.com/henriquesebastiao/downtify/tree/2.0.0) (2026-04-23)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.1.4...2.0.0)

**Implemented enhancements:**

- Feature Request: pagination in search [\#70](https://github.com/henriquesebastiao/downtify/issues/70)

## [1.1.4](https://github.com/henriquesebastiao/downtify/tree/1.1.4) (2026-02-19)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.1.3...1.1.4)

**Fixed bugs:**

- Search engine does not return results [\#102](https://github.com/henriquesebastiao/downtify/issues/102)
- fix: for Error code 500 with spotify API and download error. [\#99](https://github.com/henriquesebastiao/downtify/issues/99)
- Error code 500 with spotify API [\#97](https://github.com/henriquesebastiao/downtify/issues/97)
- Error: Request failed with status code 500 [\#92](https://github.com/henriquesebastiao/downtify/issues/92)
- Error when searching album [\#88](https://github.com/henriquesebastiao/downtify/issues/88)
- 500 Internal Server Error on download [\#85](https://github.com/henriquesebastiao/downtify/issues/85)
- ERROR: Your application has reached a rate/request limit [\#69](https://github.com/henriquesebastiao/downtify/issues/69)

## [1.1.3](https://github.com/henriquesebastiao/downtify/tree/1.1.3) (2026-02-18)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.1.2...1.1.3)

**Fixed bugs:**

- Download Error [\#67](https://github.com/henriquesebastiao/downtify/issues/67)
- Adding a corrected version of spotDL to reflect the changes made to the Spotify API [\#100](https://github.com/henriquesebastiao/downtify/pull/100) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Closed issues:**

- ERROR:    Client 1...b not found [\#68](https://github.com/henriquesebastiao/downtify/issues/68)

**Merged pull requests:**

- build\(deps-dev\): Bump ruff from 0.15.0 to 0.15.1 [\#98](https://github.com/henriquesebastiao/downtify/pull/98) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump vue from 3.5.27 to 3.5.28 in /frontend [\#96](https://github.com/henriquesebastiao/downtify/pull/96) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump axios from 1.13.4 to 1.13.5 in /frontend [\#95](https://github.com/henriquesebastiao/downtify/pull/95) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump daisyui from 5.5.14 to 5.5.18 in /frontend [\#94](https://github.com/henriquesebastiao/downtify/pull/94) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump ruff from 0.14.14 to 0.15.0 [\#93](https://github.com/henriquesebastiao/downtify/pull/93) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump @vitejs/plugin-vue from 6.0.3 to 6.0.4 in /frontend [\#90](https://github.com/henriquesebastiao/downtify/pull/90) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump vue-router from 5.0.0 to 5.0.2 in /frontend [\#89](https://github.com/henriquesebastiao/downtify/pull/89) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump vue-router from 4.6.4 to 5.0.0 in /frontend [\#84](https://github.com/henriquesebastiao/downtify/pull/84) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump axios from 1.13.3 to 1.13.4 in /frontend [\#83](https://github.com/henriquesebastiao/downtify/pull/83) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update packages \(2026-01-26\) [\#82](https://github.com/henriquesebastiao/downtify/pull/82) ([henriquesebastiao](https://github.com/henriquesebastiao))
- build\(deps\): Bump vue from 3.5.26 to 3.5.27 in /frontend [\#81](https://github.com/henriquesebastiao/downtify/pull/81) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump uuid from 9.0.1 to 13.0.0 in /frontend [\#80](https://github.com/henriquesebastiao/downtify/pull/80) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump daisyui from 4.12.24 to 5.5.14 in /frontend [\#79](https://github.com/henriquesebastiao/downtify/pull/79) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump axios from 1.13.2 to 1.13.3 in /frontend [\#78](https://github.com/henriquesebastiao/downtify/pull/78) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update packages \(2026-01-25\) [\#77](https://github.com/henriquesebastiao/downtify/pull/77) ([henriquesebastiao](https://github.com/henriquesebastiao))
- build\(deps-dev\): Bump @vitejs/plugin-vue from 5.2.4 to 6.0.3 in /frontend [\#74](https://github.com/henriquesebastiao/downtify/pull/74) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump vite from 5.4.21 to 7.3.1 in /frontend [\#72](https://github.com/henriquesebastiao/downtify/pull/72) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps-dev\): Bump ruff from 0.14.13 to 0.14.14 [\#71](https://github.com/henriquesebastiao/downtify/pull/71) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump actions/checkout from 5 to 6 [\#65](https://github.com/henriquesebastiao/downtify/pull/65) ([dependabot[bot]](https://github.com/apps/dependabot))

## [1.1.2](https://github.com/henriquesebastiao/downtify/tree/1.1.2) (2026-01-14)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.1.1...1.1.2)

**Closed issues:**

- Cannot download songs from web gui [\#66](https://github.com/henriquesebastiao/downtify/issues/66)
- Failure downloading [\#62](https://github.com/henriquesebastiao/downtify/issues/62)
- \[Error\] Can't download on CasaOS [\#61](https://github.com/henriquesebastiao/downtify/issues/61)

**Merged pull requests:**

- build\(deps\): Bump actions/checkout from 4 to 5 [\#55](https://github.com/henriquesebastiao/downtify/pull/55) ([dependabot[bot]](https://github.com/apps/dependabot))

## [1.1.1](https://github.com/henriquesebastiao/downtify/tree/1.1.1) (2025-10-28)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.1.0...1.1.1)

**Implemented enhancements:**

- Updating dependencies, yt-dlp to version 2025.10.22 [\#53](https://github.com/henriquesebastiao/downtify/pull/53) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Fixed bugs:**

- YT-DLP error when running via docker command [\#52](https://github.com/henriquesebastiao/downtify/issues/52)

**Closed issues:**

- Bug: client\_id parameter breaks Spotify URL \(500 Internal Server Error\) [\#50](https://github.com/henriquesebastiao/downtify/issues/50)

## [1.1.0](https://github.com/henriquesebastiao/downtify/tree/1.1.0) (2025-10-13)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.0.3...1.1.0)

**Implemented enhancements:**

- Set download directories and `web_gui_location` via environment variables [\#46](https://github.com/henriquesebastiao/downtify/issues/46)
- Added the list file view [\#45](https://github.com/henriquesebastiao/downtify/pull/45) ([lapentad](https://github.com/lapentad))

## [1.0.3](https://github.com/henriquesebastiao/downtify/tree/1.0.3) (2025-10-09)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.0.2...1.0.3)

**Closed issues:**

- Better label the Docker image [\#42](https://github.com/henriquesebastiao/downtify/issues/42)

## [1.0.2](https://github.com/henriquesebastiao/downtify/tree/1.0.2) (2025-10-09)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.0.1...1.0.2)

**Merged pull requests:**

- Labeling Docker image and updating CI dependencies [\#43](https://github.com/henriquesebastiao/downtify/pull/43) ([henriquesebastiao](https://github.com/henriquesebastiao))
- build\(deps\): Bump astral-sh/setup-uv from 3 to 7 [\#36](https://github.com/henriquesebastiao/downtify/pull/36) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump python from 3.13-alpine to 3.14-alpine [\#35](https://github.com/henriquesebastiao/downtify/pull/35) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump actions/setup-python from 5 to 6 [\#34](https://github.com/henriquesebastiao/downtify/pull/34) ([dependabot[bot]](https://github.com/apps/dependabot))
- build\(deps\): Bump actions/checkout from 4 to 5 [\#33](https://github.com/henriquesebastiao/downtify/pull/33) ([dependabot[bot]](https://github.com/apps/dependabot))

## [1.0.1](https://github.com/henriquesebastiao/downtify/tree/1.0.1) (2025-10-09)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/1.0.0...1.0.1)

**Implemented enhancements:**

- Optimizing Docker image [\#32](https://github.com/henriquesebastiao/downtify/pull/32) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Fixed bugs:**

- Error AnyIO worker thread on Umbrel [\#26](https://github.com/henriquesebastiao/downtify/issues/26)
- `AnyIO worker thread` error when trying to download music [\#9](https://github.com/henriquesebastiao/downtify/issues/9)

**Closed issues:**

- 🚀 Roadmap [\#12](https://github.com/henriquesebastiao/downtify/issues/12)

## [1.0.0](https://github.com/henriquesebastiao/downtify/tree/1.0.0) (2025-10-08)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.3.2...1.0.0)

**Implemented enhancements:**

- Implementing new download interface [\#30](https://github.com/henriquesebastiao/downtify/pull/30) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Closed issues:**

- \[Resolved\] Bug Report: FFmpeg conversion error on Downtify 0.3.2 [\#29](https://github.com/henriquesebastiao/downtify/issues/29)
- ffmpeg erro v0.3.1 [\#28](https://github.com/henriquesebastiao/downtify/issues/28)
- Error ffmpeg [\#25](https://github.com/henriquesebastiao/downtify/issues/25)
- ffmpeg error [\#24](https://github.com/henriquesebastiao/downtify/issues/24)
- Error on UmbrelOS: application has reached a rate/request limit [\#23](https://github.com/henriquesebastiao/downtify/issues/23)
- quality adjustment [\#16](https://github.com/henriquesebastiao/downtify/issues/16)

## [0.3.2](https://github.com/henriquesebastiao/downtify/tree/0.3.2) (2025-03-31)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.3.1...0.3.2)

**Implemented enhancements:**

- \[Feature request/bug\] Make port for web UI adjustable [\#20](https://github.com/henriquesebastiao/downtify/issues/20)
- 🔧 feat: Set container web port via environment variable - fix \#20 [\#21](https://github.com/henriquesebastiao/downtify/pull/21) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Fixed bugs:**

- ERROR:spotdl.download.progress\_handler:FFmpegError: Failed to convert [\#19](https://github.com/henriquesebastiao/downtify/issues/19)
- 🔧 fix: Fix error when running ffmpeg - fix \#19 [\#22](https://github.com/henriquesebastiao/downtify/pull/22) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Closed issues:**

- Question on VPNs? [\#17](https://github.com/henriquesebastiao/downtify/issues/17)

## [0.3.1](https://github.com/henriquesebastiao/downtify/tree/0.3.1) (2025-03-10)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.3.0...0.3.1)

**Fixed bugs:**

- hx-get="/list-downloads/" is producing a 404 [\#14](https://github.com/henriquesebastiao/downtify/issues/14)

**Merged pull requests:**

- Fixes `hx-get="/list-downloads/"` producing a 404 error [\#15](https://github.com/henriquesebastiao/downtify/pull/15) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [0.3.0](https://github.com/henriquesebastiao/downtify/tree/0.3.0) (2025-03-10)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.2.4...0.3.0)

**Implemented enhancements:**

- Add downloaded music list to web interface [\#11](https://github.com/henriquesebastiao/downtify/issues/11)
- is it safe to have the client id and the client secret inside the code? [\#10](https://github.com/henriquesebastiao/downtify/issues/10)
- Adding `/list` endpoint to view downloaded songs [\#13](https://github.com/henriquesebastiao/downtify/pull/13) ([dvelayosmd](https://github.com/dvelayosmd))

## [0.2.4](https://github.com/henriquesebastiao/downtify/tree/0.2.4) (2025-03-05)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.2.3...0.2.4)

**Implemented enhancements:**

- Documenting API and adding tests [\#7](https://github.com/henriquesebastiao/downtify/pull/7) ([henriquesebastiao](https://github.com/henriquesebastiao))

**Closed issues:**

- Create documentation with Material for MkDocs [\#5](https://github.com/henriquesebastiao/downtify/issues/5)
- Documenting API with Swagger UI [\#4](https://github.com/henriquesebastiao/downtify/issues/4)

**Merged pull requests:**

- 📜 docs: Adding documentation with MkDocs [\#8](https://github.com/henriquesebastiao/downtify/pull/8) ([henriquesebastiao](https://github.com/henriquesebastiao))
- Sync dev with main [\#6](https://github.com/henriquesebastiao/downtify/pull/6) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [0.2.3](https://github.com/henriquesebastiao/downtify/tree/0.2.3) (2025-03-03)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.2.2...0.2.3)

## [0.2.2](https://github.com/henriquesebastiao/downtify/tree/0.2.2) (2025-02-24)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.2.1...0.2.2)

**Merged pull requests:**

- 🔧 Adding improvements for version 0.2.2 [\#3](https://github.com/henriquesebastiao/downtify/pull/3) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [0.2.1](https://github.com/henriquesebastiao/downtify/tree/0.2.1) (2025-02-08)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.2.0...0.2.1)

**Merged pull requests:**

- 🔧 fix: Running SpotDL with subprocess avoiding async errors [\#2](https://github.com/henriquesebastiao/downtify/pull/2) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [0.2.0](https://github.com/henriquesebastiao/downtify/tree/0.2.0) (2025-02-07)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/0.1.0...0.2.0)

**Implemented enhancements:**

- ✨ Adding web interface with Bootstrap [\#1](https://github.com/henriquesebastiao/downtify/pull/1) ([henriquesebastiao](https://github.com/henriquesebastiao))

## [0.1.0](https://github.com/henriquesebastiao/downtify/tree/0.1.0) (2025-02-06)

[Full Changelog](https://github.com/henriquesebastiao/downtify/compare/28292c064ed8d50fbdca0b6bc7a47f65f8772cd6...0.1.0)
