# Verificación de UMS Control 1.0.0

[English](../VERIFICATION.md)

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

**No está validado el funcionamiento del servidor en Windows 10/11 nativo.** La JVM y FFmpeg oficiales Windows arrancan bajo Wine, pero la prueba temporal de UMS falla al obtener entropía criptográfica del sistema mediante JNA/SecureRandom. Es una limitación concreta del entorno disponible; no demuestra que Windows nativo funcione ni falle. No había un equipo Windows disponible. La candidata Windows no debe presentarse como versión estable plenamente aceptada hasta verificar allí instalación, inicio/reinicio/parada, autoinicio, búsqueda, administración, entrega DLNA y cortafuegos.

Una sesión gráfica Linux limpia real con systemd de usuario, las combinaciones de escritorio/controlador, la reproducción física, NVENC y sesiones prolongadas no quedan sustituidas por pruebas aisladas o sintéticas. Se han probado entornos Ubuntu 22.04/24.04; las demás distribuciones con glibc 2.35+ son objetivos de compatibilidad, no sistemas certificados individualmente.

Algunos dispositivos pueden no ser compatibles al 100 %. No se clasifica ningún fabricante como incompatible.

Los registros y las comprobaciones privadas del anfitrión quedan fuera de las fuentes públicas. SHA256SUMS se genera tras cerrar los paquetes y PUBLIC-MANIFEST.json identifica las fuentes públicas exactas.

Auditoría ELF Linux: 470 archivos comprobados, versión máxima requerida de símbolos GLIBC 2.35.
