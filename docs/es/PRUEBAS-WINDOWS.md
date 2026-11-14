# Windows 1.0.0 — verificación estable

[English](../WINDOWS-TESTING.md)

El instalador Windows x86-64 forma parte de la [release estable UMS Control 1.0.0](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0), junto al DEB/ZIP Linux. Instalación por usuario, sin administrador; se conservan ajustes, perfiles y carpetas existentes.

## Comprobaciones nativas Windows 11

- Instalación/sustitución, conservación del idioma, rutas Unicode, autoprueba y cierre limpio.
- Inicio, salud, parada/reinicio, reparación y prevención de arranques duplicados de UMS 15.9.0.
- Detección de Ethernet/Wi-Fi físicos; adaptadores virtuales y desconectados excluidos.
- Codificación del lanzador y rutas específicas de Windows.
- Catálogo asociado a la IP configurada explícitamente al cambiar el UUID UPnP de la TV; prioridad del UUID configurado.
- Nombres personalizados visibles al reabrir y al cambiar la identidad del renderer.
- Icono Windows en aplicación, instalador, desinstalador y accesos.

## Aceptación de reproducción y sesión confirmada por el usuario

El 2026-11-14 el usuario confirmó navegación/reproducción en TV, pausa/reanudación y saltos. Después confirmó las pruebas finales de la versión corregida: reinicio/autoinicio activado y desactivado, y reproducción prolongada con audio, subtítulos y pistas alternativas. Son resultados físicos comunicados por el usuario, diferenciados de las mediciones automáticas.

## Paquete y verificación automatizada

El instalador estable conserva el ejecutable corregido aceptado en Windows nativo e incluye la documentación estable actualizada. Pasaron 170 regresiones, 168 vistas y cinco escenarios DLNA aislados, además de reconstrucción Java y payload mínimo. Instalación/sustitución, autoprueba, apertura/cierre, iconos y retirada del instalador final conservando preferencias se comprueban por separado de la aceptación física.

Windows 11 es el sistema verificado de forma nativa; Windows 10 es un objetivo de compatibilidad. La compatibilidad varía según dispositivo, códec, firmware y controlador. La codificación hardware necesita equipo/controladores apropiados; no se garantiza reproducción universal. No se publican perfiles, medios, direcciones ni registros privados.
