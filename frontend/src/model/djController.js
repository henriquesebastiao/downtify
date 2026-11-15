import { computed, ref, watch } from 'vue'
import { v4 as uuid } from 'uuid'
import { musicAI } from './musicAI'
import { usePlayer } from './player'
import { createDjStream } from './djStream'
import { createDjDiagnostics } from './djDiagnostics'
import { djPresentation, djResumePoint } from './djPresentation'
import { normalizeTrack } from '/src/lib/library'
import { useUi } from './ui'

const session = ref(null)
const busy = ref(false)
const notice = ref('')
const failure = ref('')
const proof = ref(null)
let serial = 0,
  timer,
  stream,
  pending,
  owner,
  reporting = false,
  sequence = 0,
  interruptions = 0
let playIntent = 0
let commandTail = Promise.resolve()
let creation = null
const available = computed(
  () => musicAI.capabilities.value?.features?.dj_interactive === true
)
const ready = computed(
  () =>
    available.value &&
    (musicAI.capabilities.value?.dj?.interactive_ready === true ||
      (musicAI.capabilities.value?.features?.dj_trial === true &&
        musicAI.capabilities.value?.dj?.interactive_trial_ready === true)) &&
    musicAI.capabilities.value?.dj?.queue_supported === true
)
const trial = () =>
  musicAI.capabilities.value?.dj?.interactive_ready !== true &&
  musicAI.capabilities.value?.features?.dj_trial === true
const player = usePlayer()

async function command(action, payload = {}) {
  const value = session.value
  if (!value || owner !== musicAI.account.value || !available.value) return
  const mine = serial,
    account = owner
  const work = commandTail
    .catch(() => {})
    .then(async () => {
      if (mine !== serial || account !== musicAI.account.value) return
      return musicAI.commandDj(value.id, {
        request_id: uuid(),
        action,
        payload,
      })
    })
  commandTail = work
  return work
}
function error(value) {
  failure.value =
    value?.response?.data?.detail ||
    value?.message ||
    'Lecture DJ indisponible.'
  useUi().toast(failure.value, { kind: 'error' })
}
function clear({ stopRemote = false } = {}) {
  const id = session.value?.id || pending?.id,
    account = owner,
    previous = commandTail
  const remote =
    !session.value ||
    session.value.mode === 'interactive' ||
    musicAI.capabilities.value?.dj_asset_consumers === true
  const request = creation
  creation = null
  if (request && stopRemote) {
    request.abort.abort()
    if (request.owner === musicAI.account.value)
      void musicAI.cancelDjRequest(request.id).catch(() => {})
  }
  serial++
  playIntent++
  commandTail = Promise.resolve()
  clearInterval(timer)
  timer = null
  pending = null
  player.armDjHandover(null)
  if (player.dj.value) player.detachDj()
  else stream?.unload()
  stream = null
  session.value = null
  busy.value = false
  if (stopRemote && id && remote)
    void previous
      .catch(() => {})
      .then(() => {
        if (account === musicAI.account.value) return musicAI.stopDj(id)
      })
      .catch(() => {})
}
async function listen(value, options = {}) {
  if (!value.tracks?.length) {
    const account = musicAI.account.value,
      mine = serial,
      selection = player.selectionVersion.value
    value = await musicAI.djSession(value.id)
    if (
      !value ||
      account !== musicAI.account.value ||
      mine !== serial ||
      selection !== player.selectionVersion.value
    )
      return
  }
  if (session.value?.id === value.id && player.dj.value) {
    player.play()
    return
  }
  clear({ stopRemote: (session.value?.id || pending?.id) !== value.id })
  session.value = value
  proof.value = null
  owner = musicAI.account.value
  const mine = serial
  const tracks = new Map(
    (value.tracks || []).map((track) => [track.id, normalizeTrack(track)])
  )
  let audibleRow, audibleBase, audibleTrack
  let node
  let ownStream
  const transport = {
    position() {
      return (
        ownStream?.position?.(session.value?.media_origin) ??
        node?.currentTime ??
        0
      )
    },
    resumePoint() {
      return djResumePoint(session.value, transport.position())
    },
    queueEntries() {
      return (session.value?.timeline || []).map((row, index) => ({
        occurrence: row.occurrence ?? index,
        track: tracks.get(row.id),
      }))
    },
    presentation(position) {
      const state = djPresentation(session.value, position)
      const base = tracks.get(state.current?.id)
      if (state.row?.start !== audibleRow || base !== audibleBase) {
        audibleRow = state.row?.start
        audibleBase = base
        audibleTrack = base
          ? { ...base, djSession: value.id, djOccurrence: audibleRow }
          : null
      }
      return {
        ...state,
        current: audibleTrack,
        next: tracks.get(state.next?.id),
        id: value.id,
        mode: value.mode,
        continuous: value.continuous === true,
      }
    },
    async play() {
      const intent = ++playIntent
      try {
        if (value.mode === 'interactive' && session.value?.state !== 'ready')
          await command('resume')
        if (mine !== serial || intent !== playIntent) return
        if (
          !(await ownStream.connect()) ||
          mine !== serial ||
          intent !== playIntent
        )
          return
        await node.play()
      } catch (reason) {
        if (mine === serial) error(reason)
      }
    },
    async pause() {
      playIntent++
      node.pause()
      try {
        if (value.mode === 'interactive' && session.value?.state !== 'ready')
          await command('pause')
      } catch (reason) {
        if (mine === serial) error(reason)
      }
    },
    async next() {
      return transport.navigate('next')
    },
    async previous() {
      return transport.navigate('previous')
    },
    async navigate(action) {
      try {
        failure.value = ''
        const position = transport.position()
        let target
        if (value.mode === 'prepared') {
          const rows = session.value?.timeline || []
          const index = rows.findIndex(
            (row) => row.start <= position && position < row.end
          )
          const start = (ordinal) =>
            Math.max(rows[ordinal]?.start || 0, rows[ordinal - 1]?.end || 0)
          const ordinal =
            action === 'next'
              ? index + 1
              : position - start(index) > 3
                ? index
                : Math.max(0, index - 1)
          if (index < 0 || !rows[ordinal])
            throw new Error('Ce repère n’est pas disponible dans le mix.')
          target = start(ordinal)
        } else {
          const result = await command(
            action,
            musicAI.capabilities.value?.dj_navigation === true
              ? { position: String(position) }
              : {}
          )
          if (mine !== serial || owner !== musicAI.account.value) return
          if (result?.accepted !== true)
            throw new Error(
              result?.reason || 'La commande DJ n’a pas pu être confirmée.'
            )
          target = result.seek_to_seconds
          if (target == null) {
            notice.value =
              'Le saut sera appliqué à la prochaine transition disponible.'
            return
          }
        }
        if (mine !== serial || owner !== musicAI.account.value) return
        const relative = node.currentTime + target - transport.position()
        if (!Number.isFinite(target) || relative < 0)
          throw new Error('Ce repère est sorti de la fenêtre du direct.')
        node.currentTime = relative
        notice.value = 'Titre sélectionné dans le mix DJ.'
      } catch (reason) {
        if (mine === serial && owner === musicAI.account.value) error(reason)
      }
    },
    seek(seconds) {
      if (value.mode === 'prepared')
        node.currentTime = (player.dj.value?.row?.start || 0) + seconds
    },
    unload() {
      ownStream?.unload()
    },
    detached() {
      if (mine !== serial) return
      const previous = commandTail,
        account = owner
      clear()
      void previous
        .catch(() => {})
        .then(() => {
          if (value.mode === 'interactive' && account === musicAI.account.value)
            return musicAI.stopDj(value.id)
        })
        .catch(() => {})
    },
  }
  const queueTracks =
    options.resumeNext !== true
      ? (value.timeline || []).map((row) => tracks.get(row.id)).filter(Boolean)
      : null
  node = player.attachDj(transport, {
    ...options,
    queueTracks,
    queueOccurrences: (value.timeline || []).map(
      (row, index) => row.occurrence ?? index
    ),
  })
  const diagnostics = createDjDiagnostics({
    enabled: () =>
      value.validation === true &&
      mine === serial &&
      owner === musicAI.account.value &&
      musicAI.capabilities.value?.administrator === true,
    media: node,
    position: transport.position,
  })
  const onInterruption = (event) => {
    if (reporting) {
      interruptions++
      diagnostics.interruption(event.type)
    }
  }
  for (const event of ['waiting', 'seeking', 'pause'])
    node.addEventListener(event, onInterruption)
  transport.unload = () => {
    ownStream?.unload()
    for (const event of ['waiting', 'seeking', 'pause'])
      node.removeEventListener(event, onInterruption)
  }
  stream =
    value.mode === 'interactive'
      ? createDjStream({
          media: node,
          url: musicAI.mediaUrl(value.media_url),
          current: () => mine === serial && owner === musicAI.account.value,
          onDiagnostic: diagnostics.stream,
          onFatal: () => error(new Error('Le direct a été interrompu.')),
        })
      : {
          async connect() {
            node.src ||= musicAI.mediaUrl(value.media_url)
            return true
          },
          unload() {},
        }
  ownStream = stream
  sequence = 0
  interruptions = 0
  reporting = false
  let polling = false
  timer = setInterval(async () => {
    if (polling || mine !== serial) return
    polling = true
    try {
      await musicAI.refresh()
      const current = await musicAI.djSession(value.id, transport.position())
      if (mine !== serial) return
      if (
        !current ||
        musicAI.capabilities.value?.features?.['dj_' + current.mode] !== true ||
        ['stopped', 'failed', 'cancelled', 'deleting'].includes(current.state)
      ) {
        clear()
        return
      }
      session.value = current
      // Render status is not a transport command. A delayed status must never
      // override the latest local pause/resume, or control a new classic track.
      for (const track of current.tracks || [])
        tracks.set(track.id, normalizeTrack(track))
      player.refreshDj(node.currentTime)
      if (
        current.validation &&
        !node.paused &&
        !node.seeking &&
        node.readyState >= 3
      ) {
        reporting = true
        const sentAt = performance.now()
        const receipt = await musicAI.continuityDj(value.id, {
          position: transport.position(),
          sequence: sequence++,
          interruptions,
        })
        if (mine === serial) {
          proof.value = receipt
          diagnostics.receipt(receipt, sentAt)
        }
      }
    } catch (reason) {
      if (
        mine === serial &&
        [401, 403, 404, 409].includes(reason?.response?.status)
      )
        clear()
    } finally {
      polling = false
    }
  }, 5000)
  await player.play()
}
async function startQueue() {
  if (busy.value) return
  const mine = serial,
    account = musicAI.account.value
  owner = account
  busy.value = true
  failure.value = ''
  await musicAI.refresh(true)
  if (mine !== serial || account !== musicAI.account.value) return
  if (!ready.value) {
    busy.value = false
    error(
      new Error('Le DJ interactif doit être activé et validé sur ce serveur.')
    )
    return
  }
  const selection = [
    player.currentTrack.value,
    ...player.upcoming.value.map((item) => item.track),
  ].filter(Boolean)
  const defer = Boolean(player.currentTrack.value)
  const queue = defer ? selection.slice(1) : selection
  if (
    queue.length < 2 ||
    queue.length > 40 ||
    queue.some((track) => !track.file || track.stream || track.isPodcast)
  ) {
    busy.value = false
    error(
      new Error(
        defer
          ? 'Ajoutez au moins deux titres locaux à suivre (40 maximum).'
          : 'Choisissez une file de 2 à 40 titres locaux.'
      )
    )
    return
  }
  const signature = selection.map((track) => track.file).join('\n')
  busy.value = true
  notice.value =
    'Préparation des transitions. Votre écoute continue ; le DJ prendra le relais au prochain titre.'
  try {
    const request = {
      id: uuid(),
      owner: account,
      abort: new AbortController(),
      origin: defer ? selection[0].file : null,
    }
    creation = request
    const value = await musicAI.createDj(
      {
        request_id: request.id,
        mode: 'interactive',
        theme: 'fete',
        queue_order: true,
        queue_files: queue.map((track) => track.file),
        trial: trial(),
      },
      { signal: request.abort.signal }
    )
    if (creation === request) creation = null
    if (mine !== serial || account !== musicAI.account.value) {
      if (account === musicAI.account.value) await musicAI.stopDj(value.id)
      return
    }
    pending = {
      id: value.id,
      signature,
      first: selection[0].file,
      owner: account,
      ready: null,
    }
    if (defer)
      player.armDjHandover(() => {
        if (!pending?.ready || pending.owner !== musicAI.account.value)
          return false
        const current = pending.ready
        void listen(current, { resumeNext: true })
        notice.value = 'Mode DJ actif · ordre de la file conservé.'
        return true
      })
    // Poll preparation without tying its lifetime to the queue panel.
    clearInterval(timer)
    let polling = false
    timer = setInterval(async () => {
      if (polling || !pending || pending.owner !== musicAI.account.value) return
      polling = true
      try {
        const current = await musicAI.djSession(pending.id)
        if (!pending || mine !== serial) return
        if (
          !current ||
          ['failed', 'stopped', 'cancelled'].includes(current.state)
        ) {
          clear()
          error(new Error('La préparation DJ a échoué.'))
          return
        }
        if (
          current.media_url &&
          ['playing', 'paused'].includes(current.state)
        ) {
          if (!defer) {
            await listen(current)
            notice.value = 'Mode DJ actif · ordre de la file conservé.'
          } else if (player.currentTrack.value?.file !== pending.first) {
            await musicAI.stopDj(pending.id)
            clear()
            notice.value =
              'Le titre a changé avant le relais. La file classique continue.'
          } else if (current.state === 'playing') {
            await musicAI.commandDj(current.id, {
              request_id: uuid(),
              action: 'pause',
              payload: {},
            })
          } else {
            pending.ready = current
            notice.value = 'Mode DJ prêt · prend le relais au prochain titre.'
          }
        }
      } catch (reason) {
        if (mine === serial) {
          error(reason)
          clear({ stopRemote: true })
        }
      } finally {
        polling = false
      }
    }, 1500)
  } catch (reason) {
    if (mine === serial) {
      if (creation?.owner === musicAI.account.value)
        void musicAI.cancelDjRequest(creation.id).catch(() => {})
      creation = null
      error(reason)
      busy.value = false
    }
  }
}
async function stop() {
  const id = session.value?.id || pending?.id
  const remote =
    !session.value ||
    session.value.mode === 'interactive' ||
    musicAI.capabilities.value?.dj_asset_consumers === true
  const previous = commandTail,
    account = musicAI.account.value
  const resume = player.desiredPlaying.value || player.isPlaying.value
  clear({ stopRemote: !id })
  if (resume) player.play()
  notice.value = 'Mode DJ désactivé. Votre file classique est conservée.'
  if (id && remote)
    try {
      await previous.catch(() => {})
      if (account === musicAI.account.value) await musicAI.stopDj(id)
    } catch (reason) {
      error(reason)
    }
}
async function startTheme(theme, style = 'library', seed = null) {
  if (busy.value || session.value) {
    error(new Error('Arrêtez le mix DJ en cours avant d’en lancer un autre.'))
    return
  }
  const account = musicAI.account.value,
    mine = serial
  owner = account
  busy.value = true
  await musicAI.refresh(true)
  if (mine !== serial || account !== musicAI.account.value) return
  if (!ready.value) {
    busy.value = false
    error(new Error('Le DJ continu nécessite un moteur interactif validé.'))
    return
  }
  if (seed && musicAI.capabilities.value?.dj_seed_mix !== true) {
    busy.value = false
    error(
      new Error(
        'Ce serveur ne prend pas encore en charge les mixes DJ à partir d’un titre.'
      )
    )
    return
  }
  const defer = Boolean(
    seed && !player.dj.value && player.currentTrack.value?.file === seed.file
  )
  busy.value = true
  try {
    const request = {
      id: uuid(),
      owner: account,
      abort: new AbortController(),
      origin: defer ? seed.file : null,
    }
    creation = request
    const created = await musicAI.createDj(
      {
        request_id: request.id,
        mode: 'interactive',
        continuous: true,
        theme,
        style,
        count: 24,
        trial: trial(),
        ...(seed ? { seed_file: seed.file, skip_seed: defer } : {}),
      },
      { signal: request.abort.signal }
    )
    if (creation === request) creation = null
    if (account !== musicAI.account.value || mine !== serial) {
      if (account === musicAI.account.value) await musicAI.stopDj(created.id)
      return
    }
    pending = {
      id: created.id,
      owner: account,
      first: defer ? seed.file : null,
      ready: null,
    }
    if (defer)
      player.armDjHandover(() => {
        if (!pending?.ready || pending.owner !== musicAI.account.value)
          return false
        const value = pending.ready
        void listen(value)
        notice.value = 'DJ continu · transitions adaptées'
        return true
      })
    notice.value = 'Préparation du DJ continu…'
    let polling = false
    timer = setInterval(async () => {
      if (polling || mine !== serial) return
      polling = true
      try {
        const value = await musicAI.djSession(created.id)
        if (mine !== serial) return
        if (
          !value ||
          ['failed', 'stopped', 'cancelled'].includes(value.state)
        ) {
          clear()
          error(new Error('La préparation du DJ continu a échoué.'))
          return
        }
        if (value.media_url && ['playing', 'paused'].includes(value.state)) {
          if (!defer) {
            await listen(value)
            notice.value = 'DJ continu · transitions adaptées'
          } else if (value.state === 'playing')
            await musicAI.commandDj(value.id, {
              request_id: uuid(),
              action: 'pause',
              payload: {},
            })
          else {
            pending.ready = value
            notice.value = 'Mix DJ prêt · relais au prochain titre.'
          }
        }
      } catch (reason) {
        if (mine === serial) {
          error(reason)
          clear()
        }
      } finally {
        polling = false
      }
    }, 2000)
  } catch (reason) {
    if (mine === serial) {
      if (creation?.owner === musicAI.account.value)
        void musicAI.cancelDjRequest(creation.id).catch(() => {})
      creation = null
      error(reason)
      busy.value = false
    }
  }
}
watch(musicAI.account, () => clear(), { flush: 'sync' })
watch(
  player.selectionVersion,
  () => {
    if (session.value || pending || busy.value) clear({ stopRemote: true })
  },
  { flush: 'sync' }
)
watch(
  () => player.currentTrack.value?.file,
  (file) => {
    const origin = creation?.origin || pending?.first
    if (origin && origin !== file) {
      clear({ stopRemote: true })
      notice.value =
        'Le titre a changé avant le relais. La lecture classique continue.'
    }
  },
  { flush: 'sync' }
)
watch(
  () => musicAI.capabilities.value?.features,
  (features) => {
    if (
      (session.value && features?.['dj_' + session.value.mode] !== true) ||
      (pending && !features?.dj_interactive)
    )
      clear()
  }
)
const startSeed = (seed) =>
  seed?.file && !seed.stream && !seed.isPodcast
    ? startTheme('fete', 'library', seed)
    : undefined
export const djController = {
  session,
  busy,
  notice,
  failure,
  proof,
  available,
  ready,
  listen,
  startQueue,
  startTheme,
  startSeed,
  stop,
}
