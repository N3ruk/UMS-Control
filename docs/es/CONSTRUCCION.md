# Construcción y verificación

[English](../BUILD.md)

Las recetas y comandos completos se mantienen en [la guía principal de construcción](../BUILD.md). Las fuentes requieren Python 3.12+, PyQt6, psutil, Send2Trash y zstandard. Los usuarios finales utilizan DEB, ZIP o EXE, que incluyen el runtime del panel.

## Ejecución desde fuentes

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python src/launcher.py
```

El código y las traducciones están en `src/`; los recursos se mantienen en `assets/`, `patches/` y `server-support/`. `python src/install.py` es el instalador opcional para desarrollo.

Las regresiones completas, la matriz visual y las comprobaciones DLNA se mantienen en privado. No hacen falta para ejecutar ni empaquetar el programa. La CI pública comprueba integridad de fuentes, compilación Python, autoprueba y reconstrucción Java. Los resultados de la release son históricos y se conservan en [VERIFICACION.md](VERIFICACION.md).

## Integración UMS

Las fuentes modificadas están en `patches/net`. Linux y Windows tienen JAR oficiales e integraciones separados, identificados por SHA256. La construcción inicial reproducible exige JDK 17; JDK 21 con `--release 17` no produce el mismo bytecode. Nunca se modifica el JAR oficial.

## DEB y ZIP Linux

```sh
python3 packaging/prepare_inputs.py
python3 packaging/build_linux.py --base /ruta/absoluta/base-ubuntu22-preparada
```

`packaging/inputs.json` fija Python y las ruedas exactas por URL, tamaño y SHA256. `server-support/dependencies-portable.json` fija paquetes nativos Ubuntu 22.04 y sus fuentes. La base necesita libcurl3-gnutls y las bibliotecas habituales X11/XCB/Wayland/fontconfig/OpenGL. El constructor requiere bwrap y dpkg-deb; no son requisitos Python del usuario final. No se incluyen libc ni controladores gráficos.

El DEB utiliza una pregunta debconf en inglés. El ZIP utiliza una pregunta de terminal en inglés con los mismos siete idiomas; `./install.sh --language en` permite instalación desatendida explícita. Se conservan las preferencias existentes.

Los recursos Linux se copian sin cambios desde `assets/`. Windows utiliza `assets/windows/`, no los fondos Linux. La exportación conserva ambos conjuntos; `tools/render_assets.py` solo permite regenerar explícitamente el arte geométrico Windows.

## EXE Windows

```sh
python packaging/prepare_inputs.py --windows
```

La preparación incorpora únicamente las ruedas verificadas al Python Windows de construcción, sin instalar pip en el sistema. La herramienta de construcción requiere `7z` en PATH. Se fijan PyInstaller 6.16.0 y pefile 2023.2.7. Con NSIS disponible:

```sh
python packaging/build_windows.py
```

La construcción cruzada utiliza Wine y NSIS aislado; los argumentos completos están en la guía inglesa. La instalación es por usuario, no ejecuta el instalador upstream de UMS ni instala un servicio de sistema. El extractor 7-Zip incluye su licencia. Ajustes, perfiles, servidor y medios quedan fuera del directorio del panel.

## Aceptación

La autoprueba se ejecuta con `ums-control --self-test` o `UMS-Control.exe --self-test --report resultado.json`. `--smoke-gui` comprueba el arranque normal; `--screenshots CARPETA` genera capturas con datos de demostración, sin aplicar ajustes del servidor.

Se deben probar instalación, actualización, retirada, selección/conservación de idioma y ciclo real del servidor en sistemas desechables. Un entorno aislado no sustituye una sesión gráfica/systemd física. Wine no certifica la red, el cortafuegos ni la reproducción física de Windows. La aceptación Windows nativa sigue siendo un requisito para añadir Windows a una release estable; la prerelease de pruebas permanece separada. Véase la [lista pendiente](PRUEBAS-WINDOWS.md).

No publicar `.cache`, perfiles ni diagnósticos privados. `packaging/public-files.json` enumera las fuentes públicas y `packaging/runtime-files.json` identifica únicamente los archivos que necesitan los paquetes instalados. Las herramientas de desarrollo no se copian al payload Linux. Tras revisar los cambios, ejecutar `python3 tools/export_public.py --update-manifest` y `python3 tools/export_public.py --check`. `--destination CARPETA` exporta a un directorio nuevo vacío. Revisar los checksums de los artefactos antes de publicar.

La nueva estructura se aplica a la rama principal y las construcciones futuras. Las etiquetas y descargas ya publicadas conservan su estructura original; esta reorganización no las sustituye.
