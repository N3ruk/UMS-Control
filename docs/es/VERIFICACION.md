# Verificación de UMS Control 1.0.0

[English](../VERIFICATION.md)

La [release estable v1.0.0](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0) incluye DEB/ZIP Linux, instalador Windows y SHA256SUMS común. Los arneses completos se mantienen privados; la CI pública comprueba integridad, compilación Python, autoprueba y Java reproducible.

| Comprobación | Resultado |
| --- | --- |
| Regresiones | 170 pruebas en Ubuntu 24.04 aislado |
| Matriz de interfaz | 168 vistas: seis temas, siete idiomas, dos tamaños y dos pestañas |
| Integración DLNA | Cinco escenarios aislados, incluido catálogo UPnP primero |
| DEB/ZIP Linux | Instalación/sustitución, autoprueba, interfaz y retirada conservando preferencias; entornos Ubuntu 22.04/24.04 |
| Compatibilidad Linux | 479 ELF auditados; requisito máximo GLIBC 2.35 |
| Windows nativo | Windows 11: instalación, servidor, adaptadores físicos, catálogo y nombres personalizados |
| Aceptación física Windows | El usuario confirma TV, pausa/saltos, reproducción prolongada con audio/subtítulos/pistas alternativas, reinicio y autoinicio activado/desactivado |
| Paquete Windows final | Ejecutable nativo aceptado conservado; documentación estable, ciclo de instalador, autoprueba, interfaz e iconos comprobados |
| Java | Entradas Linux/Windows separadas e integración correspondiente; reconstrucción reproducible JDK 17 |
| Capturas | Linux: renderizados reales del DEB. Windows: EXE instalado bajo Wine. Datos de demostración |

La [verificación Windows](PRUEBAS-WINDOWS.md) distingue pruebas automáticas de resultados comunicados por el usuario. Windows 11 está verificado de forma nativa; Windows 10 es un objetivo de compatibilidad. Linux requiere x86-64, glibc 2.35+ y X11/Wayland; otras combinaciones de distribución/controlador no se certifican individualmente. La compatibilidad de dispositivos/medios varía.

No se publican registros, perfiles ni medios privados. `packaging/source-manifest.json` identifica las fuentes. El repositorio conserva las fuentes y recetas; la release adjunta paquetes/checksums, sin ZIP adicional de fuentes.
