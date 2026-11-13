# Prerelease Windows: aceptación nativa pendiente

[English](../WINDOWS-TESTING.md)

**Estado: solo para pruebas.** El EXE pertenece a [v1.0.0-windows-rc1](https://github.com/N3ruk/UMS-Control/releases/tag/v1.0.0-windows-rc1). No se incluye en la release estable Linux v1.0.0. El instalador y la aplicación siguen mostrando la versión 1.0.0; el tag prerelease identifica su estado de aceptación.

## Qué se ha comprobado realmente

**Solo bajo Wine**: instalación NSIS por usuario, apertura normal de la aplicación Qt, autoprueba, capturas inglesas, conservación de idioma/preferencias al sustituir la misma versión y desinstalación. Se verificaron los componentes UMS Windows y su integración Java independiente. Estos resultados no validan Windows 10/11 nativo.

La JVM y FFmpeg oficiales Windows arrancan bajo Wine, pero la prueba temporal del servidor UMS falla durante la inicialización de entropía del sistema con JNA/SecureRandom. Este fallo del entorno de pruebas no demuestra que el servidor funcione ni falle en Windows nativo. No se disponía de equipo Windows nativo.

## Pendiente antes de añadir Windows a una release estable

Todos los puntos siguientes están **pendientes en Windows 10/11 x86-64 nativo**, con una cuenta normal sin administrador. Registrar la compilación exacta de Windows, checksum del instalador, resultados y correcciones/repeticiones. Un resultado en una versión de Windows no certifica la otra.

- [ ] Instalar y abrir el EXE; elegir el idioma inicial, cambiarlo después y comprobar rutas con espacios/caracteres no ASCII.
- [ ] Sustituir/reinstalar y desinstalar el panel; comprobar que conserva ajustes, perfiles y medios originales, y que solo afecta al proceso/autoinicio del servidor gestionado.
- [ ] Instalar el runtime oficial UMS desde el panel, superar su prueba temporal y alcanzar la administración localhost con salud correcta; comprobar reparación, actualización/recuperación de fallos y retirada del servidor sin borrar configuración ni medios.
- [ ] Iniciar, parar y reiniciar UMS real; consultar salud y registros y verificar que no quedan procesos gestionados duplicados o huérfanos.
- [ ] Activar/desactivar autoinicio y cerrar/abrir sesión para comprobar ambos estados sin derechos de administrador.
- [ ] Elegir la interfaz IPv4 de la LAN, descubrir dispositivos y comprobar permisos/avisos del cortafuegos en red privada, administración limitada a localhost y acceso DLNA desde otro dispositivo físico.
- [ ] Navegar/buscar desde un cliente DLNA real; comprobar aislamiento de carpetas por dispositivo, exclusión de clientes sin configurar y del anfitrión, sin renombrar ni modificar medios originales.
- [ ] Reproducir originales y conversión manual/automática en un cliente físico; comprobar audio/subtítulos, saltos, reinicio/aplicación de ajustes y sesión prolongada. Verificar NVENC por separado si se afirma soporte de codificación NVIDIA.

Cuando estas pruebas pasen y los fallos estén corregidos y comprobados de nuevo, podrá añadirse el instalador Windows a una release estable. Hasta entonces permanece como **prerelease** independiente, aunque instalador e interfaz funcionen bajo Wine.

Algunos dispositivos pueden no ser compatibles al 100 %; estas pruebas no certifican todos los dispositivos, códecs o firmwares. No publicar medios personales, direcciones privadas ni registros sin anonimizar en los informes.
