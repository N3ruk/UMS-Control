# Compatibilidad y límites de verificación

[English](../COMPATIBILITY.md)

| Destino | Paquete | Verificación real |
| --- | --- | --- |
| Linux x86-64, glibc 2.35+ | DEB / ZIP | Entornos de usuario aislados Ubuntu 22.04 y 24.04; el escritorio anfitrión es Linux. Consultar el informe para los ciclos de instalación probados. |
| Windows 10/11 x86-64 | EXE | Instalador estable; pruebas nativas Windows 11 y confirmación del usuario de TV y autoinicio. Windows 10 es un objetivo de compatibilidad. |
| ARM, 32 bits, musl/Alpine, macOS | Ninguno | No soportados por estos paquetes binarios. |

El ZIP incluye Python, Qt y las bibliotecas nativas privadas necesarias, basadas en Ubuntu 22.04. No instala paquetes Debian en el sistema operativo ni requiere APT/RPM, Python del sistema, pip o compilador. Linux requiere escritorio gráfico, controladores gráficos compatibles y glibc 2.35 o posterior. Pueden funcionar más distribuciones, pero solo se certifican las configuraciones realmente probadas. Un entorno aislado no equivale a una sesión gráfica/systemd física.

Linux utiliza systemd de usuario si está disponible o, en otro caso, un proceso gestionado por usuario. Windows utiliza la misma aplicación con proceso gestionado y entrada de inicio de sesión del usuario. Antes de controlar un proceso se comprueban su PID y su instante de creación. No se instala un servicio Windows de administrador.

Algunos dispositivos pueden no ser **compatibles al 100 %**. La compatibilidad depende del dispositivo, su firmware y los formatos multimedia, no simplemente del fabricante. Original conserva los bytes, no garantiza los códecs del cliente. Las pruebas de protocolo o la generación de una conversión no certifican reproducción física.

La búsqueda utiliza IPv4 local. Las aplicaciones que comparten IP no tienen perfiles independientes basados en esa dirección. Se excluye el propio servidor de la búsqueda. El cortafuegos Windows puede solicitar permiso para la LAN privada seleccionada; no se alteran sus reglas silenciosamente. Wine no permite validar esa interacción nativa.

La integración inicial tiene compilaciones Linux/Windows separadas y reproducibles contra sus respectivos JAR de UMS 15.9.0 y Java 17. Las versiones estables posteriores se preparan, recompilan cuando procede, comprueban y prueban antes de sustituir la instalación. Una versión futura incompatible puede rechazarse conservando la anterior. La recompilación requiere un JDK apropiado.

NVIDIA requiere hardware y controladores compatibles. Las pruebas CPU por sí solas no certifican codificación hardware ni todos los formatos. Los registros, perfiles, medios y diagnósticos privados quedan fuera de las fuentes públicas.

EXE Windows y DEB/ZIP Linux se distribuyen juntos en la estable 1.0.0. Véase la [verificación Windows](PRUEBAS-WINDOWS.md).
