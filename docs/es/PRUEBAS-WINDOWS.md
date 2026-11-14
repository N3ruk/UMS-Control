# Prerelease Windows: aceptación nativa parcial

[English](../WINDOWS-TESTING.md)

**Estado: solo para pruebas.** El EXE público sigue siendo [v1.0.0-windows-rc1](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0-windows-rc1), separado de Linux estable. Sus archivos no se han sustituido. Instalador e interfaz conservan la versión 1.0.0.

## EXE publicado frente a candidata corregida

Las pruebas nativas Windows 11 del 2026-11-14 descubrieron defectos de cierre, codificación/propiedad del lanzador de autoinicio y tratamiento de carpetas Unicode en RC1. Las correcciones se han probado en una **candidata privada de desarrollo**; todavía no están en el EXE descargable. No atribuir los resultados de la candidata corregida al instalador publicado.

Las pruebas Wine anteriores cubrían NSIS, panel y conservación de preferencias, pero JNA/SecureRandom impedía probar el servidor. Windows 11 nativo, compilación 26300.9974, sí ejecuta el servidor real; aquel límite de Wine no es un fallo nativo del servidor.

## Comprobado en Windows 11 nativo

Con usuario normal sin administrador y medios sintéticos:

- Instalación NSIS por usuario en ruta con espacios, español y japonés; elección inicial de idioma, sustitución conservando preferencias, autoprueba del ejecutable y cierre limpio de la interfaz.
- Comprobación de disposición Qt nativa: 168 vistas, seis temas y siete idiomas. No sustituye una revisión manual de usabilidad.
- Runtime oficial UMS 15.9.0, prueba temporal Java/JNA nativa, administración localhost saludable, inicio/parada/reinicio y prevención de arranques duplicados.
- Reparación, retirada e instalación nueva del servidor desde la interfaz del ejecutable corregido; desinstalación del panel conservando ajustes, perfiles y medios. Una descarga corrupta se rechaza sin sustituir el runtime activo. No se instaló una versión superior del servidor.
- Propiedad/activación/desactivación del autoinicio y ejecución real mediante Windows Script Host del lanzador empaquetado desde ruta Unicode. **No se cerró/abrió sesión ni reinició Windows.**
- Entrega LAN a otro ordenador Linux físico: navegación por carpeta Unicode, exclusión de carpeta ajena, originales idénticos por hash, GET/HEAD y rangos de bytes; FFmpeg Windows convierte realmente en modos manual/automático, con pistas de audio y rutas de subtítulos incrustados/separados. Los clips sintéticos no validan reproducción en TV/consola ni percepción de audio/subtítulos.
- DLNA accesible desde LAN; administración limitada a localhost e inaccesible desde el otro ordenador. Sin modificar cortafuegos; falta probar los avisos y permitir/denegar en un equipo limpio.
- Instalación, datos, procesos gestionados, accesos, registro, autoinicio y temporales de prueba retirados; solo archivos propios de la prueba a papelera. Medios personales y nodo nativo OpenClaw intactos.

Regresiones completas de fuentes: 163 pruebas, 168 vistas, cuatro escenarios DLNA reales aislados, reconstrucción Java reproducible y payload mínimo correctos. Son resultados de desarrollo, no una nueva publicación binaria.

## Pendiente para aceptación estable Windows

- [ ] Instalador corregido definitivo y fuentes/checksums exactos de su entrega.
- [ ] Cerrar/abrir sesión con autoinicio activado/desactivado; reinicio/reconexión si se afirma.
- [ ] Aviso de cortafuegos en equipo limpio/red privada, permitir/denegar y selección del adaptador previsto.
- [ ] Navegación y reproducción en TV/consola física, audio/subtítulos y saltos; aislamiento entre varios clientes configurados, cliente sin configurar y anfitrión en la red objetivo.
- [ ] Sesión prolongada, aplicación/reinicio de ajustes y recuperación de interrupciones; NVENC por separado antes de afirmar codificación hardware.
- [ ] Actualización real a una versión oficial UMS superior y recuperación de un fallo de activación.
- [ ] Windows 10 nativo antes de afirmar pruebas en Windows 10 y 11.

Windows sigue como **prerelease** independiente. No se certifican todos los dispositivos, códecs, controladores ni firmwares. No publicar medios privados, direcciones de red ni registros sin anonimizar.
