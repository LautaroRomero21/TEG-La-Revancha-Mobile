# Informe técnico — TEG La Revancha v16 a Android

## Fuentes analizadas

- RAR `TEG_La_Revancha.rar`: contiene código PC **v16** (4 módulos de motor, Pygame, tests y recursos) y reglamento de 40 páginas. Es la fuente adoptada.
- ZIP `TEG_La_Revancha_Turnos_Colores_Tarjetas_v2.zip`: fuente histórica v2, **no** empleada para sobrescribir v16.

## Estado del análisis y migración

| Parte | Origen | Intervención | Evidencia |
| --- | --- | --- | --- |
| Tablero (72 países, 7 continentes) | `data.py` v16 | Copia idéntica | Regresión 126/126 |
| Reglas y bots | `logic.py` v16 | Copia idéntica | Regresión 126/126 |
| Pactos, agresiones, guarniciones | `pactos.py` v16 | Copia idéntica | Regresión 126/126 |
| Respuestas bot | `respuestas_pactos.py` v16 | Copia idéntica | Regresión 126/126 |
| Eventos PC | `main.py` Pygame | Nuevo controlador sin Pygame | Pruebas específicas |
| Renderer PC | `renderer.py` Pygame | Nuevo `main.py` Kivy | Código, **sin prueba gráfica** |
| Mapa/cartas/iconos | Carpeta v16 | Reutilización | Existencia de archivos |
| APK | Buildozer | Spec y workflow preparados | **No compilado** |

## Flujo de juego

La lógica original mantiene **preparación** (dos incorporaciones iniciales cuando corresponda), barrera de refuerzos de todos los participantes, **ataques → reagrupamiento → tarjetas**, rotación del primer jugador por ronda, canjes con progresión propia, misiles y diplomacia. El adaptador nunca recalcula dados, fronteras, premios ni objetivos: llama a los métodos públicos del motor.

## Riesgos principales

- **Crítico:** no confundir pruebas unitarias del motor con compilación, instalación y ejecución real del APK. Android/SDL/Kivy requiere build y prueba en dispositivo.
- **Alto:** `Scatter` multitáctil y transformaciones de coordenadas; validación visual en el celular.
- **Alto:** diálogos largos de pactos y situaciones; revisar scroll y accesibilidad táctil.
- **Medio:** imagen del mapa original muy grande (`mapa.jpg` de 9933×7016); usar para APK la versión `mapa_ui.jpg` de 1200×900, idéntica a la usada por el renderer PC v16, para ahorrar memoria; el archivo de alta resolución no se altera en la fuente.
- **Medio:** rendering de animaciones durante ataques encadenados y notificaciones de bot a alta velocidad.
- **Medio:** la discrepancia **20 objetivos mencionados / 19 del anexo** ya existía en v16, no es una decisión de Android.

## Plan de continuación y criterio de aceptación

1. Compilar APK debug en Ubuntu/WSL2 o GitHub Actions. Si Buildozer falla, corregir las dependencias **sin modificar las reglas**.
2. Ejecutar Android en dispositivo real y recorrer una partida contra 1 bot (preparación → segunda ronda), verificando zoom, fichas y popups obligatorios.
3. Probar 1 humano vs 5 bots, mapa bajo carga, compra/conversión de misiles, 4 dados, tarjetas, canjes y distintos perfiles.
4. Probar pactos: rechazo/aceptación, ruptura diferida, zonas, ataques conjuntos, condominio, elección de guarnición y reagrupamientos especiales.
5. Comparar resultados del motor v16 entre versión de PC y Android mediante fixtures/simulación determinista.
6. Recién después de resolver fallos de UX/ejecución y repetir pruebas, declarar versión Android funcional/estable.
