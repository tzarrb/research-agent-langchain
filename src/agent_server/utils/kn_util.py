import importlib
import json
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

from config.settings import Settings
from utils.log_util import build_logger


logger = build_logger("llm-util")


def get_kb_path(knowledge_name: str):
    return os.path.join(Settings.basic_settings.KN_ROOT_PATH, knowledge_name)


def get_doc_path(knowledge_name: str):
    return os.path.join(get_kb_path(knowledge_name), "content")


def get_vs_path(knowledge_name: str, vector_name: str):
    return os.path.join(get_kb_path(knowledge_name), "vector_store", vector_name)


def get_file_path(knowledge_name: str, doc_name: str):
    doc_path = Path(get_doc_path(knowledge_name)).resolve()
    file_path = (doc_path / doc_name).resolve()
    if str(file_path).startswith(str(doc_path)):
        return str(file_path)
