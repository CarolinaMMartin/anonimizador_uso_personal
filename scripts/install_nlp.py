"""Install the pinned runtime and the verified Spanish spaCy model."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACY_MODEL = 'es_core_news_md'
MODEL_VERSION = '3.8.0'
MODEL_URL = ('https://github.com/explosion/spacy-models/releases/download/'
             f'{SPACY_MODEL}-{MODEL_VERSION}/{SPACY_MODEL}-{MODEL_VERSION}-py3-none-any.whl')


def main() -> None:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')])
    sys.path.insert(0, str(ROOT))
    import spacy
    from app.runtime_paths import spacy_model_dir

    try:
        nlp = spacy.load(spacy_model_dir() or SPACY_MODEL)
        if nlp.meta.get('version') == MODEL_VERSION:
            print(f'Modelo disponible: {SPACY_MODEL} {MODEL_VERSION}')
            return
    except OSError:
        pass
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', MODEL_URL])
    print('Modelo instalado. Verificá con: python scripts/verify_nlp.py')


if __name__ == '__main__':
    main()
