# Uso e instalación

[English](../USAGE.md)

1. Instalar el panel según el README. Abrir la pestaña **Resumen**, instalar el servidor y después iniciarlo. La instalación y el inicio son acciones independientes; el autoinicio de sesión es opcional.
2. En **Dispositivos**, buscar en la red local o añadir un dispositivo mediante su IPv4 local. Los perfiles nuevos no comparten contenido. Seleccionar un dispositivo y añadir sus carpetas; los medios deben estar montados y ser legibles.
3. **Original** entrega los archivos sin modificaciones ni límites de conversión. La conversión manual utiliza las reglas seleccionadas; el modo automático adapta el contenido cuando corresponde. Los modos de conversión sitúan los vídeos en Transcode e incluyen una opción de original sin conversión.
4. Configurar audio, subtítulos y calidad cuando se utilice conversión. Cambiar la resolución máxima propone un bitrate editable. Una elección manual posterior se conserva hasta volver a cambiar de resolución. Cambiar de perfil no sobrescribe los valores guardados.
5. Los nombres anunciados compatibles modifican títulos y direcciones DLNA, no nombres de archivos. Las excepciones y reinclusiones de carpetas afectan únicamente al dispositivo seleccionado. Copiar ajustes conserva la identidad y las reglas de carpetas del destino.
6. **Guardar y aplicar** activa los ajustes de reproducción. Reinicia un servidor activo e interrumpe la reproducción; no inicia un servidor detenido. Los cambios de tema e idioma son independientes.
7. **Resumen** incluye salud, registro, reparación, actualización y retirada del servidor. Las actualizaciones estables de UMS requieren confirmación explícita. Actualizar el catálogo no actualiza el programa del servidor. La retirada conserva ajustes y medios y envía a la papelera únicamente los binarios gestionados.

El menú **Instrucciones** contiene la guía traducida. Consultar los [límites de compatibilidad](COMPATIBILIDAD.md): una respuesta HTTP correcta no demuestra la reproducción física en todos los dispositivos.

## Instalación y retirada según el formato

**DEB:** instalar mediante APT y responder la pregunta de idioma, presentada en inglés. **ZIP:** extraer y ejecutar `./install.sh` como usuario del escritorio; `--language es` permite una instalación no interactiva. **Windows:** ejecutar el instalador EXE sin derechos de administrador y seleccionar el idioma inicial. Las preferencias existentes se conservan; el idioma puede cambiarse posteriormente desde el menú **Idioma**.

Si los binarios del servidor UMS ya no se necesitan, retirarlos primero desde **Resumen**. El panel se retira mediante APT en sistemas Debian, `~/.local/share/ums-control/uninstall.sh` en la instalación ZIP o **Configuración → Aplicaciones** en Windows. Se conservan ajustes, perfiles y medios. La retirada del panel Windows/ZIP detiene su servidor gestionado y desactiva su autoinicio, pero conserva los binarios del servidor.
