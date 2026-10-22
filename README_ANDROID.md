# TEG La Revancha — Migración Android v16 (primera implementación)

**Estado de esta entrega:** código fuente Android + motor completo reutilizado + pruebas del adaptador.
**NO hay un APK compilado ni probado en teléfono.** Esta entrega requiere compilación en Linux/WSL2/GitHub Actions y validación táctil en hardware real.

## Arquitectura elegida

Se eligió **Python + Kivy + Buildozer**, porque `logic.py`, `data.py`, `pactos.py` y `respuestas_pactos.py` no importan Pygame y son aprovechables tal cual. La documentación oficial de Kivy recomienda Buildozer para Android. No se incorporó Java/Kotlin ni servicios online.

```text
TEG_La_Revancha_Android_v16/
  main.py                  Interfaz táctil Kivy, panorámica
  controller.py            Adaptador sin Kivy/Pygame entre UI y motor v16
  engine/
    logic.py               Motor v16 SIN CAMBIOS
    data.py                Grafo de los 72 países SIN CAMBIOS
    pactos.py              Diplomacia v16 SIN CAMBIOS
    respuestas_pactos.py  Respuestas a negociaciones SIN CAMBIOS
  assets/
    mapa_ui.jpg            Tablero 1200x900 optimizado original
    iconos_cartas/         Iconos de figuras de países originales
    iconos_ui/             Misil original
    objetivos_imagenes/    19 objetivos ilustrados originales
  tests/                   Nuevas pruebas del controlador móvil
  desktop_reference/       Código gráfico PC v16 + sus 126 pruebas originales
  reference/               Reglamento y PDF de tarjetas originales (no van en APK)
  buildozer.spec           Configuración Android offline y horizontal
  .github/workflows/       Build de APK mediante GitHub Actions (no ejecutado)
  ejecutar_pruebas.sh      Pruebas de regresión originales y del adaptador
```

La **versión de escritorio entregada en el RAR no ha sido modificada**. Los 4 módulos de `engine/` se copiaron byte a byte. La interfaz PC sigue siendo independiente.

## Controles móviles

- **Modo horizontal**. Deslizá un dedo para desplazar el mapa y usá dos dedos para zoom; los tokens son seleccionables con un toque breve. Tocá una ficha propia para seleccionar el origen y otra para el destino. Tocá el mismo origen para deseleccionar.
- En **incorporación**, tocá tu país, pulsá `+ EJÉRCITOS` y elegí cuánto reforzar (o «todos posibles»). La partida cambia automáticamente de fase cuando terminás de incorporar, como en el motor PC. Es posible añadir misiles nuevos o convertir ejércitos existentes.
- En **ataque**, seleccioná origen propio y destino rival, pulsá `ATACAR` o `LANZAR MISIL`. Los dados son automáticos. Si hay conquista, se exige confirmar la cantidad de ejércitos que ocupan el país.
- En **reagrupamiento**, seleccioná dos países propios limítrofes y elegí la cantidad que desplazás. También se pueden mover misiles.
- `CARTAS` muestra los símbolos y las cartas disponibles, permite elegir una combinación manual o hacer canje automático; `PEDIR TARJETA` usa las restricciones del motor v16.
- `OBJETIVO` abre la tarjeta ilustrada de la misión secreta. `PANEL` muestra datos de los participantes, situación, refuerzos, historial, pactos y control de velocidad de bots. La diplomacia incluye no agresión, ruptura, zonas, asaltos programados y proposiciones de los bots.
- Las **situaciones desde ronda 2**, las respuestas a propuestas de bots y las conquistas con traslado pendiente requieren decisión explícita. Durante una negociación, es posible tocar el mapa para inspeccionar, sin provocar movimientos.
- Animaciones de rutas, incorporación y movimiento se pueden activar o desactivar en el menú inicial; no son acciones que cambien el motor. En el panel también se puede cambiar la velocidad de los bots (Pausa, 1x, 2x, 4x, 8x).

La interfaz está desarrollada independientemente de Pygame. **No se ha verificado todavía el comportamiento real del multitouch ni el renderizado en pantalla Android**: el primer build tiene que servir para detectar ajustes necesarios en Kivy y diferencias entre dispositivos.

## Pruebas disponibles

Linux o WSL2:

```bash
cd TEG_La_Revancha_Android_v16
./ejecutar_pruebas.sh
```

Ejecuta las **126 pruebas de regresión de v16** usando las referencias gráficas de Pygame sin importarlo en el runtime Android, y **15 pruebas nuevas** de API/tacto del controlador, turnos, situaciones, pactos, objetivos y cartas. Aparte de eso, `python -m py_compile main.py controller.py engine/*.py` valida sintaxis.

## Abrir con Kivy en PC (para depuración de la nueva interfaz)

Para probar interfaz y pantallas en PC antes de generar el APK, instalá Python compatible y Kivy:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-desktop.txt
python main.py
```

En Windows usá `.venv\Scripts\activate` en PowerShell. Kivy puede necesitar librerías de gráficos/SDL específicas de cada plataforma. La ventana es horizontal.

## Generar el APK en Windows 11 usando WSL2

1. Abrí PowerShell como administrador: `wsl --install -d Ubuntu`, completá la instalación y reiniciá cuando se solicite.
2. Abrí Ubuntu, trabajá **en el filesystem de Linux** (por ejemplo `~/tegandroid`) en lugar de una ruta bajo `/mnt/c`.
3. Instalá las dependencias de Buildozer según la [guía oficial de Buildozer](https://github.com/kivy/buildozer/blob/master/docs/source/installation.rst): Python 3.10+, Java 17, `git zip unzip`, `autoconf`, `libtool`, `pkg-config`, `cmake`, `zlib`, `libffi` y herramientas de compilación. En Ubuntu compatible:

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv \
  autoconf libtool pkg-config cmake zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo6 libffi-dev libssl-dev automake autopoint gettext libltdl-dev
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip buildozer cython virtualenv
./ejecutar_pruebas.sh
buildozer -v android debug
```

El primer build necesita **Internet en la computadora compiladora** para descargar SDK/NDK y dependencias. **La app instalada no requiere Internet.** Si falla la compilación, revisar la compatibilidad puntual de Python, NDK, Kivy y python-for-android según el mensaje de error. Si termina con éxito, buscar un APK bajo `bin/` y transferirlo al celular.

## Alternativa: GitHub Actions

Crear un repositorio privado, subir **el contenido de esta carpeta**, entrar a `Actions → Compilar APK Android → Run workflow`, y, **si la compilación termina exitosamente**, descargar el artefacto `TEG-La-Revancha-APK-debug`. No hace falta publicar la aplicación en Play Store. La acción fue preparada, **no ejecutada**.

## Cómo instalar el APK debug

Transferir el APK compilado al celular Android, abrirlo desde Archivos y permitir «Instalar aplicaciones desconocidas» para el explorador que lo ejecuta. Si aparece una advertencia de seguridad, verificar el origen del archivo y no habilitar la opción globalmente. La generación de APK debug no equivale a un APK release firmado para distribución.

## Aspectos pendientes / limitaciones reconocidas

1. **Compilación y ejecución reales**: sin SDK/NDK instalado ni emulador Android en este entorno, no se verificó un APK.
2. **Interfaz Kivy**: pendiente revisión visual y táctil real con distintas densidades, resoluciones y relaciones de aspecto; probar especialmente precisión de selección, dos dedos y presentación de textos largos.
3. **Fidelidad visual**: las animaciones son una adaptación nueva (ruta, halos, cambios de color). Su aspecto no es idéntico fotograma a fotograma al de Pygame; las transiciones, las cartas y los pactos requieren prueba visual manual.
4. **Paridad funcional integral**: el motor mantiene las reglas, pero una campaña completa de juego usando solamente los controles Android (incluidos todos los casos raros de diplomacia, guarniciones y recompensas) **todavía no ha sido validada en un dispositivo**. No se considera la migración terminada.
5. **Reglamento vs implementación**: el PDF oficial (pág. 6) habla de **20 objetivos**; la implementación PC v16 documenta **19 objetivos impresos en el anexo** y cuenta con 19 imágenes. Se conservó la conducta v16 sin inventar una vigésima misión.
6. **Motor y velocidad de los bots**: los bots ejecutan un paso por evento Kivy `Clock`, no hilos paralelos; así se evita ejecutar mutaciones del tablero desde otro hilo. Evaluar rendimiento en hardware.
7. **Sin multijugador online** ni permisos de red. La capacidad futura de juego online queda como trabajo separado.

> Las imágenes y el reglamento se incluyen como material aportado para este proyecto personal. Verificar los derechos de uso antes de publicar/distribuir públicamente el software y material del juego.

## Documentación

- [Guía Kivy de empaquetado Android](https://kivy.org/doc/stable/guide/packaging-android.html)
- [Buildozer instalación](https://github.com/kivy/buildozer/blob/master/docs/source/installation.rst)
