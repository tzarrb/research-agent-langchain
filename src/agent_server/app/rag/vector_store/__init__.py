# """
# This module provides a dynamic importer for vector store services.
# It allows for lazy loading of vector store service classes based on a predefined mapping.
# """
# from typing import Any

# from langchain._api import create_importer

# _module_lookup = {
#     "VsPGService": "agent_server.app.rag.vector_store",
#     "VsRelytService": "agent_server.app.rag.vector_store",
#     "VsESService": "agent_server.app.rag.vector_store",
# }

# importer = create_importer(__package__, module_lookup=_module_lookup)


# def __getattr__(name: str) -> Any:
#     return importer(name)


# __all__ = list(_module_lookup.keys())
