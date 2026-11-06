import { computed, ref, watch } from 'vue'
import { v4 as uuid } from 'uuid'
import { musicAI } from './musicAI'
import { usePlayer } from './player'
import { createDjStream } from './djStream'
import { djPresentation } from './djPresentation'
import { normalizeTrack } from '/src/lib/library'
import { useUi } from './ui'

const session = ref(null)
const busy = ref(false)
const notice = ref('')
const failure = ref('')
const proof = ref(null)
let serial = 0, timer, stream, pending, owner, reporting = false, sequence = 0, interruptions = 0
const available = computed(() => musicAI.capabilities.value?.features?.dj_interactive === true)
const ready = computed(() => available.value && musicAI.capabilities.value?.dj?.interactive_ready === true && musicAI.capabilities.value?.dj?.queue_supported === true)
const player = usePlayer()

async function command(action) {
  const value = session.value
  if (!value || owner !== musicAI.account.value || !available.value) return
  await musicAI.commandDj(value.id, { request_id: uuid(), action, payload: {} })
}
function error(value) {
  failure.value = value?.response?.data?.detail || value?.message || 'Lecture DJ indisponible.'
  useUi().toast(failure.value, { kind: 'error' })
}
function clear() {
  serial++
  clearInterval(timer)
  timer = null
  pending = null
  player.armDjHandover(null)
  stream?.unload()
  stream = null
  if (player.dj.value) player.detachDj()
  session.value = null
  busy.value = false
}
async function listen(value, options = {}) {
  clear()
  session.value = value
  proof.value = null
  owner = musicAI.account.value
  const mine = serial
  const tracks = new Map((value.tracks || []).map(track => [track.id, normalizeTrack(track)]))
  let audibleRow, audibleBase, audibleTrack
  let node
  const transport = {
    position() { return stream?.position?.(session.value?.media_origin) ?? node?.currentTime ?? 0 },
    presentation(position) {
      const state = djPresentation(session.value, position)
      const base = tracks.get(state.current?.id)
      if (state.row?.start !== audibleRow || base !== audibleBase) {
        audibleRow = state.row?.start; audibleBase = base
        audibleTrack = base ? { ...base, djSession: value.id, djOccurrence: audibleRow } : null
      }
      return { ...state, current: audibleTrack, next: tracks.get(state.next?.id),
        id: value.id, mode: value.mode, continuous: value.continuous === true }
    },
    async play() {
      try {
        if (value.mode === 'interactive') await command('resume')
        if (mine !== serial) return
        if (!await stream.connect() || mine !== serial) return
        await node.play()
      } catch (reason) { if (mine === serial) error(reason) }
    },
    async pause() { try { if (value.mode === 'interactive') await command('pause') } catch (reason) { error(reason) } },
    async next() { try { await command('next'); notice.value = 'Le saut sera appliqué à la prochaine transition disponible.' } catch (reason) { error(reason) } },
    seek(seconds) { if (value.mode === 'prepared') node.currentTime = (player.dj.value?.row?.start || 0) + seconds },
    unload() { stream?.unload() },
  }
  node = player.attachDj(transport, options)
  const onInterruption = () => { if (reporting) interruptions++ }
  for (const event of ['waiting', 'seeking', 'pause']) node.addEventListener(event, onInterruption)
  transport.unload = () => {
    stream?.unload()
    for (const event of ['waiting', 'seeking', 'pause']) node.removeEventListener(event, onInterruption)
  }
  stream = value.mode === 'interactive' ? createDjStream({ media: node, url: musicAI.mediaUrl(value.media_url),
    current: () => mine === serial && owner === musicAI.account.value, onFatal: () => error(new Error('Le direct a été interrompu.')) }) :
    { async connect() { node.src ||= musicAI.mediaUrl(value.media_url); return true }, unload() {} }
  sequence = 0; interruptions = 0; reporting = false
  let polling = false
  timer = setInterval(async () => {
    if (polling || mine !== serial) return
    polling = true
    try {
      await musicAI.refresh()
      const values = await musicAI.djSessions()
      if (mine !== serial) return
      const current = values.find(item => item.id === value.id)
      if (!current || musicAI.capabilities.value?.features?.['dj_' + current.mode] !== true || ['stopped', 'failed', 'cancelled', 'deleting'].includes(current.state)) { clear(); return }
      session.value = current
      if (current.state === 'paused' && !node.paused) node.pause()
      for (const track of current.tracks || []) tracks.set(track.id, normalizeTrack(track))
      player.refreshDj(node.currentTime)
      if (current.validation && !node.paused && !node.seeking && node.readyState >= 3) {
        reporting = true
        const receipt = await musicAI.continuityDj(value.id, { position: transport.position(), sequence: sequence++, interruptions })
        if (mine === serial) proof.value = receipt
      }
    } catch (reason) { if (mine === serial && [401,403,404,409].includes(reason?.response?.status)) clear() }
    finally { polling = false }
  }, 5000)
  await transport.play()
}
async function startQueue() {
  if (busy.value) return
  const mine = serial, account = musicAI.account.value
  busy.value = true
  failure.value = ''
  await musicAI.refresh(true)
  if (mine !== serial || account !== musicAI.account.value) return
  if (!ready.value) { busy.value = false; error(new Error('Le DJ interactif doit être activé et validé sur ce serveur.')); return }
  const selection = [player.currentTrack.value, ...player.upcoming.value.map(item => item.track)].filter(Boolean)
  const defer = player.isPlaying.value
  const queue = defer ? selection.slice(1) : selection
  if (queue.length < 2 || queue.length > 40 || queue.some(track => !track.file || track.stream || track.isPodcast)) {
    busy.value = false; error(new Error(defer ? 'Ajoutez au moins deux titres locaux à suivre (40 maximum).' : 'Choisissez une file de 2 à 40 titres locaux.')); return
  }
  const signature = selection.map(track => track.file).join('\n')
  busy.value = true
  notice.value = 'Préparation des transitions. Votre écoute continue ; le DJ prendra le relais au prochain titre.'
  try {
    const value = await musicAI.createDj({ request_id: uuid(), mode: 'interactive', theme: 'fete',
      queue_order: true, queue_files: queue.map(track => track.file) })
    if (mine !== serial || account !== musicAI.account.value) return
    pending = { id: value.id, signature, first: selection[0].file, owner: account, ready: null }
    if (defer) player.armDjHandover(() => {
      if (!pending?.ready || pending.owner !== musicAI.account.value) return false
      const current = pending.ready
      void listen(current, { resumeNext: true })
      notice.value = 'Mode DJ actif · ordre de la file conservé.'
      return true
    })
    // Poll preparation without tying its lifetime to the queue panel.
    clearInterval(timer)
    timer = setInterval(async () => {
      if (!pending || pending.owner !== musicAI.account.value) return
      try {
        const values = await musicAI.djSessions()
        if (!pending || mine !== serial) return
        const current = values.find(item => item.id === pending.id)
        if (!current || ['failed','stopped','cancelled'].includes(current.state)) { clear(); error(new Error('La préparation DJ a échoué.')); return }
        if (current.media_url && ['playing','paused'].includes(current.state)) {
          if (!defer) {
            await listen(current)
            notice.value = 'Mode DJ actif · ordre de la file conservé.'
          } else if (player.currentTrack.value?.file !== pending.first) {
            await musicAI.stopDj(pending.id)
            clear()
            notice.value = 'Le titre a changé avant le relais. La file classique continue.'
          } else if (current.state === 'playing') {
            await musicAI.commandDj(current.id, { request_id: uuid(), action: 'pause', payload: {} })
          } else {
            pending.ready = current
            notice.value = 'Mode DJ prêt · prend le relais au prochain titre.'
          }
        }
      } catch (reason) { error(reason); clear() }
    }, 1500)
  } catch (reason) { error(reason); busy.value = false }
}
async function stop() {
  const id = session.value?.id || pending?.id
  clear()
  notice.value = 'Mode DJ désactivé. Votre file classique est conservée.'
  if (id) try { await musicAI.stopDj(id) } catch (reason) { error(reason) }
}
async function startTheme(theme, style = 'library') {
  if (busy.value || session.value) { error(new Error('Arrêtez le mix DJ en cours avant d’en lancer un autre.')); return }
  const account = musicAI.account.value, mine = serial
  busy.value = true
  await musicAI.refresh(true)
  if (mine !== serial || account !== musicAI.account.value) return
  if (!ready.value) { busy.value = false; error(new Error('Le DJ continu nécessite un moteur interactif validé.')); return }
  busy.value = true
  try {
    const created = await musicAI.createDj({request_id: uuid(), mode:'interactive', continuous:true, theme, style, count:24})
    if (account !== musicAI.account.value || mine !== serial) return
    pending = {id:created.id, owner:account}
    notice.value = 'Préparation du DJ continu…'
    let polling = false
    timer = setInterval(async () => {
      if (polling || mine !== serial) return
      polling = true
      try {
        const values = await musicAI.djSessions()
        if (mine !== serial) return
        const value = values.find(item => item.id === created.id)
        if (!value || ['failed','stopped','cancelled'].includes(value.state)) { clear(); error(new Error('La préparation du DJ continu a échoué.')); return }
        if (value.media_url && ['playing','paused'].includes(value.state)) { await listen(value); notice.value = 'DJ continu · transitions adaptées' }
      } catch (reason) { if (mine === serial) { error(reason); clear() } }
      finally { polling = false }
    }, 2000)
  } catch (reason) { if (mine === serial) { error(reason); busy.value = false } }
}
watch(musicAI.account, clear)
watch(() => musicAI.capabilities.value?.features, features => {
  if ((session.value && features?.['dj_' + session.value.mode] !== true) || (pending && !features?.dj_interactive)) clear()
})
export const djController = { session, busy, notice, failure, proof, available, ready, listen, startQueue, startTheme, stop }
