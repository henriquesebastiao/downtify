---
icon: lucide/hard-drive
---

# Ajustes del servidor

**Ajustes → Servidor** reúne cómo funciona el propio servidor. Solo lo ven los administradores (consulta [Usuarios e inicio de sesión](users.md#admins-and-users)).

## Cambiar el puerto

Downtify escucha en el puerto **8000**. Un administrador puede elegir otro en **Ajustes → Servidor → Puerto** (1024–65535):

- **Guardar** lo conserva para la próxima vez que arranque el servidor.
- **Guardar y reiniciar** reinicia el servidor en él de inmediato. Las descargas en curso se detienen, y las páginas y las apps se reconectan. Una página abierta en la dirección del propio servidor (p. ej., `http://nas:8000`) espera al servidor y abre la nueva dirección por sí sola; sigues con la sesión iniciada.

Cuando el puerto viene de la variable de entorno `DOWNTIFY_PORT` (o `PORT`) o de `--port` en la línea de comandos — que siempre mandan —, el campo muestra el puerto en uso pero no se puede editar, y la página indica cuál lo establece. Quítala (y reinicia) para elegir el puerto en Ajustes.

::: warning La red bridge de Docker asigna un puerto fijo
En la configuración predeterminada de Docker (`ports: - '8000:8000'`), el puerto del contenedor tiene que coincidir con la asignación. Tras cambiarlo en Ajustes, cambia la asignación al nuevo puerto (`'9000:9000'`) y vuelve a crear el contenedor — o ejecútalo con `network_mode: host`. Si no, no se podrá acceder a Downtify. Para volver a entrar, define `DOWNTIFY_PORT` con el puerto anterior: tiene prioridad sobre Ajustes.
:::

Detrás de un [proxy inverso](mobile-apps.md#behind-a-reverse-proxy), apunta también el proxy al nuevo puerto. Las [apps vinculadas](mobile-apps.md) usan la dirección que se les dio: tras cambiar el puerto, introduce la nueva en la app.
