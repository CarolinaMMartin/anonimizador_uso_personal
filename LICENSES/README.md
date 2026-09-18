# Licencias de terceros

Los textos de esta carpeta acompañan la distribución. Los avisos originales de cada componente prevalecen sobre los resúmenes.

| Archivo | Referencia |
|---------|------------|
| MIT.txt | Componentes bajo MIT, incluidos FastAPI, Presidio y la librería spaCy |
| Apache-2.0.txt | python-multipart y aiofiles |
| BSD-3-Clause.txt | Componentes BSD; consultar también los avisos particulares |
| GPL-3.0.txt | Referencia de la licencia del modelo spaCy |

En el portable, `models/es_core_news_md/LICENSE` contiene la licencia original del modelo. El constructor copia las licencias encontradas en las distribuciones instaladas a `LICENSES/third_party/` y genera `LICENSES/INVENTARIO_BUILD.json`, con nombres, versiones y rutas de esos avisos.

El inventario corresponde al entorno de compilación y puede incluir herramientas de desarrollo. No reemplaza las licencias originales ni implica que todas las distribuciones del entorno se utilicen durante la ejecución.

Consultar [THIRD_PARTY_NOTICES.txt](../THIRD_PARTY_NOTICES.txt) y [COMPLIANCE.md](../docs/COMPLIANCE.md) en el repositorio. En la entrega portable, ambos archivos están en la raíz del paquete.
