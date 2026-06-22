# Contribuir al Anonimizador Judicial

Gracias por interesarte en mejorar el proyecto! Esta guía resume cómo
preparar el entorno, abrir issues, mandar pull requests y mantener la
calidad del detector.

Antes de empezar, leé el [Código de Conducta](CODE_OF_CONDUCT.md). Para
reportes de seguridad usá [SECURITY.md](SECURITY.md), no un issue
público.

## Filosofía del proyecto

- **100 % local.** Todo el procesamiento corre en `127.0.0.1`. No
  agregamos llamadas a APIs externas ni dependencias de red en runtime. Esto puede parecer una obviedad, pero vale la pena aclarar. 
- **Sin LLMs ni OCR.** La detección se basa en regex + Presidio + spaCy
  (modelo local). Si una mejora requiere modelos pesados o GPU, primero
  abrí un issue para discutir si encaja. Nuestro objetivo era mantenerlo liviano para poder llegar a todo tipo de usuarios. Hemos realizado pruebas con LLM (Qween 2.5 y 3.0, obteniendo muy buenos resultados. La incorporación del LLM mejoro la detección de entidades y relaciones iniciales. 
- **Pensado para juzgados, defensorías y estudios jurídicos.** La UI
  prioriza claridad sobre features, y el flujo respeta el control humano
  (revisión, edición, exportación). Este fue el objetivo inicial, puede ser (relativamente facil) adaptado a otros entornos. Se deberia tener en cuenta: modificación de etiquetas predeterminadas y la incorporacción de regex especificas al campo. 

## Setup de desarrollo

Requisitos: **Python 3.10 o superior** y, opcionalmente, Windows si vas
a generar el `.exe` portable.

```powershell
git clone <url-del-fork>
cd anonimizador-judicial
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt -r requirements-dev.txt
python scripts/install_nlp.py   # descarga es_core_news_md (~40 MB)
python scripts/run_dev.py       # levanta http://127.0.0.1:8787
```

`requirements.txt` tiene las dependencias de runtime; `requirements-dev.txt`
suma `pytest` y `pyinstaller` (sólo necesarias para correr la suite y
generar el ZIP portable).

Verificá las capas NLP en <http://127.0.0.1:8787/health>: `presidio` y
`spacy` deben aparecer en `true`.

## Tests

Cualquier cambio sobre detectores, filtros o exportadores debe incluir
tests. La suite usa **pytest**:

```powershell
.venv\Scripts\python -m pytest tests/ -v
```

Casos típicos:

- Falsos positivos en producción → agregá una fila al CSV mental y un
  test parametrizado en `tests/test_detection_filters.py`.
- Bug en un exportador (DOCX / PDF / Markdown) → agregá fixture en
  `tests/test_pdf_export.py` o similar.
- Cambios en regex argentinos → reutilizá ejemplos reales **anonimizados**
  (nunca pegues datos personales en tests).

## Estilo de código

- Python: **PEP 8**, anotaciones de tipo cuando aportan, docstrings en
  funciones públicas.
- Frontend: HTML/CSS/JS plano, sin frameworks ni CDN. Mantener
  compatibilidad con navegadores actuales (Edge / Chrome / Firefox).
- Mensajes de commit en español o inglés; preferimos descripciones
  cortas en imperativo (ej.: `fix(detector): rechazar Ley XXX como
  patente`).
- Evitá agregar dependencias nuevas. Si es imprescindible, justifícalo
  en el PR y actualizá `requirements.txt`, `THIRD_PARTY_NOTICES.txt` y
  `NOTICE` (si la licencia lo requiere).

## Cómo contribuir un cambio

1. Abrí un **issue** describiendo el bug o la mejora antes de codear
   cambios grandes. Para typos / docs pequeños podés ir directo al PR.
2. Hacé fork y branch desde `main`. Nombre sugerido:
   `fix/organismo-narrativa`, `feat/markdown-export`,
   `docs/contributing`.
3. Codeá, agregá tests y verificá que `pytest` pase en local.
4. Abrí un **pull request** completando la plantilla. Incluí:
   - Qué problema resuelve.
   - Cómo lo verificaste (tests + pasos manuales si aplica).
   - Si modificás detectores, ejemplos de entrada / salida.
5. Una persona del equipo de IALAB revisará. Puede haber rondas de
   feedback. Los cambios se mergean por *squash* para mantener el log
   limpio.

## Áreas en las que estamos trabajando:

- **Diccionarios.** Sumar variantes regionales de nombres, apellidos y
  fórmulas judiciales (`data/dictionaries/`). Nada de datos reales,
  sólo listas genéricas.
- **Regex argentinos.** El catálogo `regex_limpio_v2.json` se puede
  ampliar con patrones nuevos (documentos, dominios, etc.).
- **Tests de regresión.** Más cobertura sobre PDF complicados (mixtos,
  con encabezados, multicolumna).
- **Performance.** El pipeline procesa documentos en chunks; mejoras a
  `app/detection/pipeline.py` o `app/extraction/` son bienvenidas.
- **Accesibilidad de la UI.** Etiquetas ARIA, navegación por teclado y
  contraste.

## No aceptamos

- Funcionalidades que requieran enviar texto del documento a servidores
  remotos / APIs en la nube.
- Modelos generativos (LLMs) corriendo dentro del proceso por defecto.
- Telemetría, analytics o tracking de uso.
- Datos personales reales en tests, fixtures, documentación o commits.

## Licencia de las contribuciones

Al enviar un pull request aceptás que tu aporte se distribuya bajo la
**licencia Apache 2.0** del proyecto. No se requiere CLA. Conservás el
copyright de tu contribución; la licencia es perpetua e irrevocable
(ver sección 5 de Apache 2.0).

Las marcas registradas y logo de IALAB **no** se ceden con la licencia
del código (ver [NOTICE](NOTICE)).
