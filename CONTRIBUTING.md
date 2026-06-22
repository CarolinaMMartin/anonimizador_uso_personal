# Contribuir al Anonimizador Judicial

¡Gracias por interesarte en mejorar el proyecto! Esta guía resume cómo
preparar el entorno, abrir issues, enviar pull requests y mantener la
calidad del detector.

Antes de empezar, leé el [Código de Conducta](CODE_OF_CONDUCT.md). Para
reportes de seguridad usá [SECURITY.md](SECURITY.md), no un issue
público.

## Filosofía del proyecto

- **Procesamiento local por defecto.** Todo el procesamiento del núcleo
  corre en `127.0.0.1`. Aunque pueda parecer una característica obvia,
  es una decisión central del proyecto: los documentos no deben enviarse
  a APIs externas ni depender de una conexión a Internet para ser
  anonimizados.

- **Núcleo liviano y accesible.** La detección actual se basa en regex,
  Presidio y spaCy con un modelo local. El objetivo es que la herramienta
  pueda ejecutarse en equipos de uso cotidiano, sin exigir GPU ni una
  infraestructura especializada.

- **Arquitectura extensible.** El núcleo no requiere LLMs ni OCR, pero
  pueden proponerse módulos opcionales que incorporen estas tecnologías.
  Un modelo adicional puede mejorar la detección, desambiguación y
  vinculación de entidades. Estas extensiones deben funcionar de manera
  local, poder desactivarse, estar documentadas y no volver obligatorio
  un entorno pesado para utilizar las funciones principales.

- **Especialización judicial con posibilidad de adaptación.** La
  herramienta fue diseñada inicialmente para juzgados, defensorías,
  fiscalías y estudios jurídicos. Parte de esa especialización se
  encuentra en los catálogos de regex y diccionarios del proyecto. Para
  adaptarla a otros ámbitos se recomienda revisar y ajustar esos recursos
  al vocabulario, documentos y entidades del nuevo dominio.

- **Control humano.** La interfaz prioriza la claridad y mantiene puntos
  explícitos de revisión, edición y verificación antes de exportar el
  documento. La detección automatizada asiste el proceso, pero no
  reemplaza la revisión de la persona usuaria.

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

`requirements.txt` contiene las dependencias de runtime;
`requirements-dev.txt` agrega `pytest` y `pyinstaller`, necesarias para
correr la suite y generar el ZIP portable.

Verificá las capas NLP en <http://127.0.0.1:8787/health>: `presidio` y
`spacy` deben aparecer en `true`.

## Tests

Cualquier cambio sobre detectores, filtros o exportadores debe incluir
tests. La suite usa **pytest**:

```powershell
.venv\Scripts\python -m pytest tests/ -v
```

Casos típicos:

- Falso positivo encontrado durante una prueba → convertí el caso en un
  ejemplo sintético y agregá un test parametrizado en
  `tests/test_detection_filters.py`.
- Bug en un exportador (DOCX / PDF / Markdown) → agregá un test en
  `tests/test_pdf_export.py` o en el archivo correspondiente.
- Cambios en regex argentinos → usá ejemplos ficticios o previamente
  anonimizados. Nunca incluyas datos personales reales en los tests.

## Estilo de código

- Python: **PEP 8**, anotaciones de tipo cuando aportan claridad y
  docstrings en funciones públicas.
- Frontend: HTML, CSS y JavaScript plano, sin frameworks ni CDN en el
  núcleo. Mantener compatibilidad con versiones actuales de Edge,
  Chrome y Firefox.
- Mensajes de commit en español o inglés, con descripciones breves en
  imperativo. Ejemplo: `fix(detector): rechazar Ley XXX como patente`.
- Evitá agregar dependencias nuevas sin necesidad. Cuando sean
  imprescindibles, justificá su incorporación en el PR y actualizá
  `requirements.txt`, `THIRD_PARTY_NOTICES.txt` y `NOTICE` cuando la
  licencia lo requiera.

## Cómo contribuir un cambio

1. Abrí un **issue** describiendo el bug o la mejora antes de desarrollar
   cambios grandes. Para correcciones menores de texto o documentación
   podés ir directamente al pull request.
2. Hacé un fork y creá una rama desde `main`. Nombres sugeridos:
   `fix/organismo-narrativa`, `feat/markdown-export` o
   `docs/contributing`.
3. Implementá el cambio, agregá tests y verificá que `pytest` pase en
   local.
4. Abrí un **pull request** completando la plantilla. Incluí:
   - qué problema resuelve;
   - cómo lo verificaste;
   - ejemplos sintéticos de entrada y salida si modificaste detectores;
   - impacto sobre rendimiento, privacidad o dependencias, si aplica.
5. Una persona mantenedora del proyecto revisará la propuesta. Puede
   haber rondas de feedback antes de incorporarla. Los cambios pueden
   integrarse mediante *squash* para mantener un historial claro.

## Áreas donde necesitamos ayuda

- **Diccionarios.** Sumar variantes regionales de nombres, apellidos y
  fórmulas judiciales en `data/dictionaries/`. Usar únicamente listas
  genéricas o datos sintéticos.
- **Regex argentinos.** Ampliar `regex_limpio_v2.json` con patrones
  adicionales para documentos, dominios y otras entidades.
- **Adaptación a otros dominios.** Crear catálogos y pruebas para áreas
  no judiciales sin alterar innecesariamente la configuración base.
- **Tests de regresión.** Aumentar la cobertura sobre PDF complejos:
  documentos mixtos, encabezados repetidos o diseños multicolumna.
- **Rendimiento.** Mejorar el procesamiento por fragmentos en
  `app/detection/pipeline.py` o los extractores de `app/extraction/`.
- **Extensiones opcionales.** Explorar OCR o modelos locales adicionales
  que mejoren la detección y relación entre entidades sin reemplazar el
  funcionamiento liviano del núcleo.
- **Accesibilidad de la interfaz.** Mejorar etiquetas ARIA, navegación por
  teclado, contraste y mensajes de estado.

## No aceptamos

- Cambios que hagan depender el flujo principal del envío de documentos
  o fragmentos de texto a servidores remotos o APIs en la nube.
- Modelos generativos, OCR u otros componentes pesados activados de forma
  obligatoria en la instalación base.
- Telemetría, analytics o seguimiento de uso.
- Datos personales reales en tests, fixtures, documentación, issues o
  commits.
- Cambios que eliminen o reduzcan la instancia de revisión humana antes
  de exportar el resultado.

## Licencia de las contribuciones

Al enviar un pull request aceptás que tu aporte se distribuya bajo la
**licencia Apache 2.0** del proyecto. No se requiere CLA. Conservás el
copyright de tu contribución y otorgás los permisos establecidos por la
licencia para su incorporación y distribución dentro del proyecto.

Las marcas y el logo de IALAB **no** se ceden con la licencia del código.
Consultá el archivo [NOTICE](NOTICE).