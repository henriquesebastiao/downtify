---
title: Deemix
icon: lucide/music
---

# Fuente de audio Deemix

Deemix es una fuente de audio opcional, desactivada por defecto. Configúrala en
**Ajustes → Fuentes de audio**, debajo de slskd, y actívala en el orden de fuentes.
Requiere tu propio servidor Deemix compatible y una cuenta de Deezer con derecho
a la calidad solicitada. No ofrece una suscripción ni se salta una.

## Credenciales y carpetas compartidas

Mantén el modo de inicio de sesión normal por sesión de Deemix. No actives el
modo de usuario único en un servidor sin protección: su endpoint de conexión devuelve el ARL compartido.

Monta en Downtify un archivo privado con tu ARL de Deezer, legible solo
por su cuenta de servicio, y define `DOWNTIFY_DEEMIX_ARL_FILE` con esa ruta.
El ARL solo se lee al abrir una sesión por cookie. Nunca se guarda en los
ajustes, ni se devuelve al navegador ni se registra en el log. Trátalo como una contraseña;
obténlo y reemplázalo en privado, no en issues ni en chats. La integración
nunca cambia el inicio de sesión ni los ajustes de descarga de Deemix para todo el servidor.
La prueba de conexión no pone descargas en cola.

| Ajuste                        | Finalidad                                                          |
| ----------------------------- | ------------------------------------------------------------------ |
| URL del servidor              | Dirección interna de Deemix, p. ej. `http://deemix:6595`           |
| Carpeta de descarga dentro de Deemix | Normalmente `/downloads`                                    |
| La misma carpeta dentro de Downtify | Bind mount compartido, p. ej. `/deemix`; se admite solo lectura |
| Calidad                       | MP3 128, MP3 320 o FLAC; los derechos no admitidos fallan de forma explícita |

La carpeta compartida se registra como carpeta de biblioteca externa al guardar.
Los archivos se quedan allí, con la organización artista/álbum de Deemix. Downtify conserva
su formato, etiquetas, carátulas y archivos `.lrc` sin reescribirlos.
La letra incrustada y los `.lrc` del mismo nombre los lee el reproductor.
Esta integración no borra, mueve ni genera ningún audio ni letra.

Un enlace de canción de Deezer selecciona esa grabación. Las descargas entre catálogos exigen
una coincidencia exacta e inequívoca de artista/título, con álbum y duración coincidentes
cuando se indican. Una coincidencia ambigua pasa a la siguiente fuente activada.
Tras completarse la cola de Deemix se comprueban el archivo y la duración/calidad.
La integración nunca limpia, cancela ni cambia trabajos manuales de Deemix.
Los enlaces explícitos de YouTube mantienen su comportamiento actual de descarga directa.

Esta fuente no reemplaza ni elimina automáticamente una canción existente de la
biblioteca. La deduplicación de la biblioteca y el reemplazo manual de audio siguen siendo independientes.
