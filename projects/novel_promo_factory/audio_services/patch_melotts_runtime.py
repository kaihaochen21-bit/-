from __future__ import annotations

import shutil
import sys
from pathlib import Path


def patch_cleaner(root: Path) -> None:
    path = root / "melo" / "text" / "cleaner.py"
    if not path.is_file():
        raise SystemExit(f"找不到 {path}")
    text = '''from importlib import import_module
import copy

_ZERO_MODULES = {"ZH": "chinese", "ZH_MIX_EN": "chinese_mix"}


def _language_module(language):
    module_name = _ZERO_MODULES.get(language)
    if not module_name:
        raise ValueError(f"此本地服务仅启用中文与中英混合：{language}")
    return import_module(f".{module_name}", __package__)


def clean_text(text, language):
    language_module = _language_module(language)
    norm_text = language_module.text_normalize(text)
    phones, tones, word2ph = language_module.g2p(norm_text)
    return norm_text, phones, tones, word2ph


def clean_text_bert(text, language, device=None):
    language_module = _language_module(language)
    norm_text = language_module.text_normalize(text)
    phones, tones, word2ph = language_module.g2p(norm_text)
    word2ph_bak = copy.deepcopy(word2ph)
    for i in range(len(word2ph)):
        word2ph[i] = word2ph[i] * 2
    word2ph[0] += 1
    bert = language_module.get_bert_feature(norm_text, word2ph, device=device)
    return norm_text, phones, tones, word2ph_bak, bert


def text_to_sequence(text, language):
    from . import cleaned_text_to_sequence
    norm_text, phones, tones, word2ph = clean_text(text, language)
    return cleaned_text_to_sequence(phones, tones, language)
'''
    path.write_text(text, encoding="utf-8")


def patch_text_init(root: Path) -> None:
    path = root / "melo" / "text" / "__init__.py"
    if not path.is_file():
        raise SystemExit(f"找不到 {path}")
    text = path.read_text(encoding="utf-8")
    start = text.index("def get_bert(")
    replacement = '''def get_bert(norm_text, word2ph, language, device):
    if language == "ZH":
        from .chinese_bert import get_bert_feature
    elif language == "EN":
        from .english_bert import get_bert_feature
    elif language == "JP":
        from .japanese_bert import get_bert_feature
    elif language == "ZH_MIX_EN":
        from .chinese_mix import get_bert_feature
    elif language in {"SP", "ES"}:
        from .spanish_bert import get_bert_feature
    elif language == "FR":
        from .french_bert import get_bert_feature
    elif language == "KR":
        from .korean import get_bert_feature
    else:
        raise ValueError(f"Unsupported language: {language}")
    return get_bert_feature(norm_text, word2ph, device)
'''
    path.write_text(text[:start] + replacement, encoding="utf-8")


def copy_unidic_fallback(root: Path) -> None:
    site = next((root / ".venv311" / "Lib" / "site-packages").glob("unidic_lite"), None)
    if not site:
        return
    source = site / "dicdir"
    target = root / ".venv311" / "Lib" / "site-packages" / "unidic" / "dicdir"
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "MeloTTS"
    patch_cleaner(root)
    patch_text_init(root)
    copy_unidic_fallback(root)
    print(f"MeloTTS runtime patched: {root}")


if __name__ == "__main__":
    main()
