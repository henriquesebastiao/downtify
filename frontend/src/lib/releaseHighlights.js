// The highlights the "What's new" dialog shows on the first visit after
// an update (components/shell/WhatsNewDialog.vue). One entry per release,
// written by hand when it's cut: a few short lines a user cares about,
// not the full changelog - the dialog links to the GitHub release for
// that. `en` is required; any other app language (a code from
// i18n/index.js) is optional and falls back to English. A release
// without an entry still gets the dialog, with only the link.
//
// Keep each line one sentence, about what the user can now do.

export default {
  '3.12.0': {
    en: [
      'Backups: save what your Downtify knows and bring it back after a lost disk or a move to a new server (Settings → Server → Backups).',
      'Sharper covers: every download aims for 1200px artwork from four sources, with an option to always embed the largest one.',
      'More lyrics: Kugou, LRCLIB search, a synced-only option and “Scan and find lyrics” for the songs you already have.',
      'Monitor shows announced releases and downloads them on release day, and finds artists by name.',
      'YouTube cookies stay signed in on their own, and a song you replaced or deleted is no longer downloaded again.',
    ],
    'pt-BR': [
      'Backups: salve o que o seu Downtify sabe e restaure depois de perder um disco ou mudar de servidor (Configurações → Servidor → Backups).',
      'Capas mais nítidas: cada download busca capas de 1200px em quatro fontes, com a opção de sempre incorporar a maior.',
      'Mais letras: Kugou, busca no LRCLIB, opção só sincronizadas e “Escanear e buscar letras” para as músicas que você já tem.',
      'O Monitor mostra lançamentos anunciados e os baixa no dia do lançamento, e encontra artistas pelo nome.',
      'Os cookies do YouTube continuam conectados sozinhos, e uma música que você substituiu ou apagou não é mais baixada de novo.',
    ],
    es: [
      'Copias de seguridad: guarda lo que sabe tu Downtify y recupéralo tras perder un disco o mudarte a otro servidor (Ajustes → Servidor → Copias de seguridad).',
      'Portadas más nítidas: cada descarga busca portadas de 1200px en cuatro fuentes, con la opción de incrustar siempre la más grande.',
      'Más letras: Kugou, búsqueda en LRCLIB, opción solo sincronizadas y “Escanear y buscar letras” para las canciones que ya tienes.',
      'El Monitor muestra los lanzamientos anunciados y los descarga el día de su salida, y encuentra artistas por nombre.',
      'Las cookies de YouTube siguen con la sesión iniciada por sí solas, y una canción que reemplazaste o borraste ya no se vuelve a descargar.',
    ],
    fr: [
      'Sauvegardes : enregistrez ce que sait votre Downtify et restaurez-le après un disque perdu ou un changement de serveur (Paramètres → Serveur → Sauvegardes).',
      'Pochettes plus nettes : chaque téléchargement vise des pochettes de 1200px depuis quatre sources, avec une option pour toujours intégrer la plus grande.',
      'Plus de paroles : Kugou, recherche LRCLIB, option paroles synchronisées uniquement et « Analyser et trouver les paroles » pour les titres déjà présents.',
      'Le Monitor affiche les sorties annoncées et les télécharge le jour de leur sortie, et trouve les artistes par leur nom.',
      'Les cookies YouTube restent connectés tout seuls, et un titre remplacé ou supprimé n’est plus retéléchargé.',
    ],
    de: [
      'Backups: Sichere, was dein Downtify weiß, und stelle es nach einer verlorenen Festplatte oder einem Serverumzug wieder her (Einstellungen → Server → Backups).',
      'Schärfere Cover: Jeder Download sucht 1200px-Cover aus vier Quellen, optional wird immer das größte eingebettet.',
      'Mehr Songtexte: Kugou, LRCLIB-Suche, eine Option nur für synchronisierte Texte und „Scannen und Songtexte suchen“ für vorhandene Titel.',
      'Der Monitor zeigt angekündigte Veröffentlichungen und lädt sie am Erscheinungstag herunter; Künstler lassen sich per Name finden.',
      'YouTube-Cookies bleiben von selbst angemeldet, und ein ersetzter oder gelöschter Titel wird nicht erneut heruntergeladen.',
    ],
  },
}
