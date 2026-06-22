"""Instala dependencias NLP según documentación Presidio.

https://microsoft.github.io/presidio/installation/
"""
import subprocess
import sys

PACKAGES = [
    "presidio-analyzer>=2.2.0",
    "presidio-anonymizer>=2.2.0",
    "spacy>=3.7.0",
]

SPACY_MODEL = "es_core_news_md"


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    run([sys.executable, "-m", "pip", "install", *PACKAGES])
    run([sys.executable, "-m", "spacy", "download", SPACY_MODEL])
    print("\nListo. Verificá con:")
    print(f"  {sys.executable} scripts/verify_nlp.py")


if __name__ == "__main__":
    main()
