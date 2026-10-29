---
icon: lucide/users
---

# Usuarios e inicio de sesión

Todos los que usan Downtify inician sesión con un **usuario y contraseña**, y cada persona puede tener su propia cuenta. Un admin gestiona las cuentas en **Ajustes → Usuarios** y ve lo que hace cada uno en **Ajustes → Actividad**.

## Iniciar sesión por primera vez

Un servidor nuevo tiene una cuenta:

| Usuario | Contraseña |
|----------|----------|
| `admin` | `downtify` |

Inicia sesión con ella y **cambia la contraseña** en **Ajustes → General → Cuenta**: quien conoce Downtify conoce la contraseña por defecto. Hasta que lo hagas, Downtify te lo recuerda tras iniciar sesión y muestra un aviso en Ajustes.

::: warning Cambia la contraseña por defecto antes de exponer el servidor
La contraseña por defecto no protege nada. Cámbiala antes de hacer Downtify accesible desde fuera de tu red doméstica — y usa HTTPS allí (consulta [Detrás de un proxy inverso](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Actualizar desde una versión antigua

Un servidor que ejecutaba una versión sin cuentas obtiene la misma cuenta `admin`, y la página de inicio de sesión lo dice una vez — hasta que un admin inicie sesión — con el usuario y la contraseña a usar:

- Si habías definido una contraseña en la antigua opción **Exigir inicio de sesión**, esa contraseña sigue valiendo para `admin`.
- Si no, es `downtify`.

Los navegadores que habían iniciado sesión antes de la actualización vuelven a iniciarla. Los teléfonos vinculados antes siguen vinculados, y ahora pertenecen a `admin`.

## Admins y usuarios

| | Admin | Usuario |
|---|---|---|
| Escuchar, buscar, descargar, dar me gusta, Descubrir, Listas de éxitos, Finder, podcasts | ✓ | ✓ |
| Vincular apps de móvil (a su propia cuenta) | ✓ | ✓ |
| Ajustes → General (su propia cuenta y preferencias), Apps, Acerca de | ✓ | ✓ |
| Todos los demás ajustes (fuentes, archivos, etiquetas, Navidrome, biblioteca, servidor), cambiar el nombre del servidor | ✓ | |
| [Compartir sus propias playlists](#sharing-playlists) (solo lectura), seguir las públicas, guardar copias | ✓ | ✓ (cuando el admin lo permite) |
| Borrar archivos y playlists (un usuario solo [lo que descargó](#deleting-songs) y sus propias playlists), gestionar sus propias vigilancias de playlists y suscripciones a podcasts, reemplazar el audio de una canción, editar fotos de artistas | ✓ | ✓ (solo lo propio) |
| [Ocultar canciones, álbumes y artistas a los usuarios](#hiding-from-users) | ✓ | |
| Gestionar usuarios, ver el registro de actividad | ✓ | |

Un usuario que intenta algo que necesita un admin recibe un mensaje que lo dice.

## Tu biblioteca

La biblioteca es compartida: cada cuenta ve todas las canciones que cualquiera descargó — en la Biblioteca, en los resultados de búsqueda marcados como descargados y en un teléfono vinculado. Los archivos nunca se guardan dos veces: cuando dos personas descargan la misma canción, llega al disco una vez, con un propietario cada una.

Los «me gusta», las playlists (descargadas y creadas en la Biblioteca) y la cola de descargas siguen siendo tuyos, salvo que seas admin — o [compartas una playlist](#sharing-playlists) para que otros la vean. La escucha es compartida — cualquiera puede reproducir, previsualizar o emitir cualquier canción, y añadir cualquier cosa a sus propias playlists. Pedir una canción que otra persona ya está descargando se une a su trabajo en lugar de obtenerla dos veces: una fila en la cola, una descarga y una propiedad cada uno — cada uno que espera ve su posición en la cola.

Los podcasts, las vigilancias de playlists y el historial de Descubrir funcionan igual: cada cuenta se suscribe a sus propios programas, sigue sus propias playlists y artistas, y entrena sus propias sugerencias. Un admin ve las filas de todas las cuentas. La escucha en sí sigue siendo compartida — cualquiera puede reproducir, previsualizar o emitir cualquier canción.

### Compartir playlists

Una playlist es privada para su propietario (y los admins) hasta que el propietario la comparte, desde **Compartir…** en la página de la playlist o en su menú **⋯**. La reproducción ya es compartida entre cuentas; esto es solo sobre quién puede *ver* una lista. Se puede compartir cualquier playlist excepto *Canciones que me gustan*, incluidas las importadas.

| Visibilidad | Quién la ve |
|------------|-------------|
| **Privada** | Solo el propietario y los admins — lo predeterminado |
| **Personas concretas** | Los usuarios que eligió el propietario |
| **Pública** | Todos en el servidor |

Las playlists de otros nunca se mezclan con las tuyas. La pestaña **Playlists** de la Biblioteca las lista en dos secciones bajo las tuyas, cada entrada con su propietario:

- **Compartidas conmigo** — playlists dirigidas a ti por nombre, siempre visibles. Una recién compartida lleva una marca **Nueva** hasta que la abres.
- **Playlists públicas** — las públicas de todos, ordenadas por propietario y nombre, con búsqueda mediante el filtro de la pestaña, mostrando el propietario, el número de canciones y si la sigues. La sección empieza plegada, y puedes ocultarla del todo con **Ajustes › General › Mostrar playlists públicas** (activado por defecto; es tuyo, como el tema).

La barra lateral también muestra algunas de las compartidas contigo y de las playlists públicas que sigues.

**Lo que puede hacer quien la ve:** reproducir, mezclar, añadir a la cola, descargar como ZIP (o a una app de móvil o de escritorio), **Seguir** una playlist pública para que se quede en sus listas — incluso con *Mostrar playlists públicas* desactivado — y sigue los cambios de su propietario, y **Guardar una copia**: una playlist privada y editable propia, con las canciones que puede ver. Quien la ve no puede editar, renombrar, borrar, compartir ni desvincular la playlist de otra persona. El propietario de una playlist de la biblioteca puede hacer editores a algunas de las personas con quienes la comparte, que también añaden y quitan canciones: consulta [Playlists colaborativas](collaborative-playlists.md).

**Dejar de compartir:** cuando el propietario vuelve a hacer privada una playlist, o quita a alguien de la lista, sale de las listas de esa persona al instante (seguida o no); una playlist que deja de ser pública ya no se sigue. Las copias que la gente ya guardó se quedan con ellos. Renombrar una playlist compartida la mantiene compartida; borrarla se lleva el compartido consigo. Las canciones que un admin [oculta a los usuarios](#hiding-from-users) quedan fuera de las canciones de una playlist compartida para ellos, como en todas partes.

Un admin puede desactivar todo esto con **Ajustes › Biblioteca › Permitir que los usuarios compartan playlists** (activado por defecto). Mientras está desactivado, todo lo compartido queda oculto y nadie puede compartir ni seguir — lo compartido vuelve al reactivarlo.

Las apps vinculadas reciben las mismas listas: [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) dice quién es el propietario de cada una y si es de solo lectura, y `playlists_changed` en el WebSocket les avisa de que se actualicen.

### Ocultar a los usuarios

Los admins deciden lo que ven las demás cuentas. Todo es visible para todos hasta que un admin oculta algo: una **canción**, un **álbum** entero o un **artista** entero. Lo oculto sale de la Biblioteca, de las marcas «en la biblioteca» de la búsqueda, de las listas de canciones de las playlists y de lo que sincroniza un teléfono vinculado — para los usuarios, no para los admins.

- **En la Biblioteca**, abre el menú `…` de una canción, álbum o artista y elige **Ocultar a los usuarios** (o **Mostrar a los usuarios** para deshacerlo). En la pestaña Canciones, selecciona varias canciones y usa **Ocultar a los usuarios** en la barra de selección.
- Los admins siguen viéndolo todo. Lo oculto lleva un pequeño ojo tachado, y su información emergente dice por qué: oculto por sí solo, con su álbum o con su artista.
- **Ajustes › Usuarios › Oculto para los usuarios** lista cada artista, álbum y canción oculta, con **Mostrar a los usuarios** junto a cada uno.
- Una canción oculta sigue oculta cuando se mueve a otra carpeta y cuando [Mejorar biblioteca](library-upgrade.md) o [Reemplazar audio](replace-audio.md) reescriben su archivo. Borrar el archivo olvida la regla.
- Una regla de álbum coincide con el artista y el título del álbum, y una regla de artista con el artista bajo el que la Biblioteca agrupa la canción — los mismos nombres que usan las pestañas Álbumes y Artistas de la Biblioteca.

::: info Ocultar trata de lo que se lista
Controla lo que ven las cuentas en la app, no quién puede obtener un archivo cuya dirección ya conoce. No lo uses para proteger archivos sensibles.
:::

Ocultar y mostrar quedan registrados en el [registro de actividad](#activity).

### Borrar canciones

Borrar una canción la quita del disco para todos, así que sigue a quien la descargó. Un admin puede borrar cualquier cosa. Un usuario puede borrar una canción que descargó él mismo; cuando otra persona descargó también la misma canción, borrar solo renuncia a su propia propiedad y la canción se queda en la biblioteca compartida. Una canción que nadie descargó mediante una cuenta (un barrido del monitor de playlists, una descarga anterior a las cuentas, una [carpeta extra](external-library.md)) solo la puede borrar un admin. Borrar una playlist tuya nunca se lleva archivos de nadie más.

### Uso por cuenta

**Ajustes › Usuarios** lista, bajo cada cuenta, lo que tiene: canciones y su tamaño, «me gusta», playlists, descargas pedidas y tráfico en ambos sentidos (obtenido del origen vs. servido a clientes), con los totales de todos debajo. «Canciones» cuenta las canciones que descargó una cuenta, no lo que puede ver.

## Tu cuenta y preferencias

**Ajustes → General** empieza con tu **Cuenta**: cambia tu usuario o contraseña, o cierra sesión. También puedes cerrar sesión desde la barra lateral (o **Más** en el móvil).

El resto de **General** — tema, idioma, mostrar letras en el reproductor, álbumes en los resultados de búsqueda — es **tuyo**: te sigue a cada navegador en el que inicias sesión y no cambia nada para nadie más.

**Ajustes → Apps** lista los teléfonos vinculados a tu cuenta (un admin ve los de todos, con su propietario). **Cerrar sesión en todas partes** desvincula tus apps y cierra tu sesión en todos los navegadores.

## Gestionar usuarios

En **Ajustes → Usuarios** un admin puede:

- **Añadir un usuario** — nombre de usuario (de 3 a 32 letras, dígitos, `.`, `-` o `_`), contraseña (al menos 8 caracteres) y rol.
- **Editar** un usuario — renombrarlo, hacerlo admin o usuario, o darle una contraseña nueva (lo que cierra su sesión en sus navegadores; sus apps siguen vinculadas).
- **Eliminar** un usuario — sus apps se desvinculan y sus navegadores cierran sesión. Sus archivos se quedan en el disco (los admins aún los ven); sus «me gusta», playlists, suscripciones a podcasts, vigilancias, historial de sugerencias y contadores de tráfico se van con él.
- **Cerrar la sesión de todos** — se desvincula cada app de cada usuario y se cierra cada navegador, también el tuyo.

Siempre hay al menos un admin: el último no se puede eliminar ni convertir en usuario, y no puedes eliminar tu propia cuenta.

## Actividad

**Ajustes → Actividad** (admins) muestra, como el panel de Jellyfin:

- **Sonando ahora** — lo que reproduce cada navegador y app, quién, en qué punto de la canción está y si está en pausa. Se actualiza cada pocos segundos.
- **Historial** — inicios de sesión (y los fallidos, con la dirección de la que venían), cierres de sesión, canciones reproducidas, descargas, «me gusta», archivos borrados, canciones ocultadas o mostradas a los usuarios, apps vinculadas y desvinculadas, cuentas añadidas, cambiadas o eliminadas, contraseñas y ajustes cambiados. Filtra por usuario o por tipo. Los ajustes guardados se listan solo por nombre, nunca por sus valores. Las entradas se conservan 90 días.

Las apps también informan de lo que reproducen — consulta el [contrato del cliente móvil](../mobile-client-contract.md#8-report-plays).

## Desactivar las cuentas

Un servidor al que solo tú llegas — en tu propio ordenador, o detrás de algo que ya pide contraseña — puede no necesitar cuentas. Define `DOWNTIFY_DISABLE_AUTH=true` (consulta [Variables de entorno](../getting-started/environment-variables.md#mobile-apps-and-sign-in)):

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Entonces:

- No hay página de inicio de sesión: quien abra Downtify lo usa como el primer admin (`admin` en un servidor nuevo).
- Los botones de cerrar sesión, **Ajustes → Usuarios**, la parte **Cuenta** de **Ajustes → General** y **Cerrar sesión en todas partes** en **Ajustes → Apps** desaparecen.
- Los teléfonos aún se pueden vincular (a ese admin), y **Ajustes → Actividad** sigue mostrando qué se reproduce dónde.
- El tema, el idioma y las demás preferencias de **General** se conservan como las de ese admin.

::: warning Cualquiera que alcance el servidor puede hacerlo todo
Con las cuentas desactivadas, nada pregunta quién eres: todos en tu red — o en internet, si el puerto está expuesto — pueden cambiar ajustes, borrar música y vincular un teléfono. No desactives las cuentas en un servidor al que otros lleguen.
:::

Ponlo en `false` (o quítalo) y se vuelve a exigir el inicio de sesión, con las cuentas, contraseñas y apps como estaban.

## ¿Olvidaste la contraseña?

Ejecuta esto en el servidor — `admin` recupera la contraseña `downtify` (y se recrea como admin si se renombró o eliminó); las demás cuentas y las apps vinculadas se dejan como están:

```bash
docker exec downtify python main.py auth-reset
```

Fuera de Docker, ejecuta `python main.py auth-reset` (o `uv run python main.py auth-reset`) en la carpeta de Downtify. Luego inicia sesión y cambia la contraseña.

## Scripts y la API

Ahora cada llamada a la API necesita credenciales (consulta la [referencia de la API](../api-reference.md#server-and-sign-in)). Un script puede iniciar sesión con `POST /api/auth/login` y conservar la cookie `downtify_session`, o usar el token de un dispositivo vinculado.
