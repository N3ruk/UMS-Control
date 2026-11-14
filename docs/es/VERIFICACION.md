# Verificación de UMS Control 1.0.0

[English](../VERIFICATION.md)

Estos son resultados históricos de la release publicada. Las regresiones completas y los arneses de interfaz/DLNA se conservan en privado y no hacen falta para ejecutar ni construir el programa. La CI pública actual comprueba la allowlist mínima, compilación, autoprueba y reconstrucción Java; no vuelve a ejecutar toda la aceptación privada de la release.

La [release Linux v1.0.0](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0) contiene el DEB y el ZIP. El EXE Windows es una [prerelease v1.0.0-windows-rc1](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0-windows-rc1) separada, pendiente de la [lista de aceptación en Windows nativo](PRUEBAS-WINDOWS.md). Publicar Linux no certifica Windows ni la compatibilidad universal de dispositivos.

| Comprobación | Resultado |
| --- | --- |
| Regresión en Ubuntu 24.04 aislado | 160 pruebas correctas; integración obligatoria, sin omisiones de integración |
| Interfaz | 168 vistas: seis temas, siete idiomas, dos tamaños y dos pestañas principales |
| Servidor portable Linux | Instalación real aislada, inicio, reinicio, activación/desactivación del autoinicio, parada y retirada de un runtime UMS desechable correctos |
| Ciclo del DEB | Instalación, sustitución por la misma versión y purga en Ubuntu 24.04 aislado; pregunta inglesa interactiva, selección inicial de alemán/francés y conservación de una preferencia japonesa |
| Ciclo del ZIP | Instalación, sustitución y retirada en Ubuntu 22.04 aislado sin Python/Qt del sistema; selección y conservación de francés |
| EXE bajo Wine | Instalación NSIS real, apertura normal, autoprueba, sustitución y desinstalación; preferencia japonesa conservada |
| Integración Java | JAR oficiales Linux y Windows separados verificados; reconstrucción Windows idéntica con JDK 17 |
| Capturas inglesas | Linux: renderizados Qt reales de los seis temas del contenido del DEB en un entorno aislado. Windows: aplicación instalada mediante EXE bajo Wine; perfiles sintéticos, sin medios privados |

## Aceptación pendiente

**RC1 Windows publicado no tiene aceptación completa.** Windows 11 nativo 26300.9974 ya ejecuta el servidor real; el fallo anterior JNA/SecureRandom era un límite de Wine. Las pruebas nativas detectaron defectos en el EXE público. Una candidata privada corregida supera instalación/sustitución/retirada, cierre, ciclo/reparación del servidor, rutas Unicode y DLNA sintético hacia otro ordenador físico. Pasan 163 pruebas de fuentes, 168 vistas y cuatro escenarios DLNA aislados. Estas correcciones no están publicadas. Siguen pendientes inicio de sesión real, cortafuegos en equipo limpio, TV/consola, sesiones prolongadas y los demás [criterios de aceptación](PRUEBAS-WINDOWS.md). Windows 10 no se ha probado.

Una sesión gráfica Linux limpia real con systemd de usuario, las combinaciones de escritorio/controlador, la reproducción física, NVENC y sesiones prolongadas no quedan sustituidas por pruebas aisladas o sintéticas. Se han probado entornos Ubuntu 22.04/24.04; las demás distribuciones con glibc 2.35+ son objetivos de compatibilidad, no sistemas certificados individualmente.

Algunos dispositivos pueden no ser compatibles al 100 %. No se clasifica ningún fabricante como incompatible.

Los registros y las comprobaciones privadas del anfitrión quedan fuera de las fuentes públicas. SHA256SUMS se genera tras cerrar los paquetes y packaging/source-manifest.json identifica las fuentes públicas exactas.

Auditoría ELF Linux: 470 archivos comprobados, versión máxima requerida de símbolos GLIBC 2.35.
