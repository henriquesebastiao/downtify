---
icon: lucide/download
---

# Avisos de actualización

Downtify consulta su propia [página de Releases de GitHub](https://github.com/henriquesebastiao/downtify/releases) una vez por hora. Cuando hay una versión más reciente, aparece un aviso al final de la barra lateral en todas las páginas — en el móvil, un punto en la pestaña **Más** y una línea en la parte superior de su hoja — y en **Ajustes → Acerca de**:

> ✦ Actualización 3.0.1 disponible

Haz clic para abrir esa versión en GitHub.

## Cómo funciona

- Una tarea en segundo plano del backend (`downtify/update_check.py`) obtiene la última versión de la API de GitHub una vez nada más arrancar y luego cada hora. Es de tipo «lanzar y olvidar»: nada en la interfaz espera por ella.
- La interfaz web lee el resultado en caché de `GET /api/check_update` (consulta la [Referencia de la API](../api-reference.md)) una vez por hora y muestra el aviso cuando encuentra una versión más reciente.
- Las versiones se comparan numéricamente (`2.10.0` < `2.9.0` es falso, a diferencia de una comparación simple de cadenas), y se ignora un prefijo `v` opcional en la etiqueta de la release.

## Si GitHub no está disponible

Una comprobación fallida (host sin conexión, límite de peticiones de GitHub) se registra en el log y simplemente se repite en la siguiente pasada horaria — el resultado anterior, si lo hay, sigue vigente hasta entonces. La comprobación nunca bloquea nada de lo que hace Downtify; no hay ningún error visible para el usuario.

## No se descarga nada automáticamente

Esto solo te *avisa* de que existe una versión nueva — Downtify no se actualiza solo. Para actualizar de verdad, descarga la nueva imagen y vuelve a crear el contenedor:

```bash
docker compose pull
docker compose up -d
```
