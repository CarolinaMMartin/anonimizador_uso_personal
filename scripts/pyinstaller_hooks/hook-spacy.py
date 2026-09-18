"""Collect spacy runtime resources while leaving development tests out."""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all(
    'spacy', include_py_files=False,
    filter_submodules=lambda name: not name.startswith(('spacy.tests', 'spacy.benchmarks')),
    exclude_datas=['**/tests/**', '**/benchmarks/**'],
)
