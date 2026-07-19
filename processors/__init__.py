import importlib

__all__ = [
    "QueryExpander",
    "PaperSearcher",
    "MetadataFilter",
    "FullTextRetriever",
    "TextExtractor",
    "FullTextFilter",
    "ProtocolExtractor",
    "ProtocolScorer",
    "ProtocolFormatter",
]

_MODULE_MAP = {
    "QueryExpander": "processors.01_query_expander",
    "PaperSearcher": "processors.02_paper_searcher",
    "MetadataFilter": "processors.03_metadata_filter",
    "FullTextRetriever": "processors.04_full_text_retriever",
    "TextExtractor": "processors.05_text_extractor",
    "FullTextFilter": "processors.06_full_text_filter",
    "ProtocolExtractor": "processors.07_protocol_extractor",
    "ProtocolScorer": "processors.08_protocol_scorer",
    "ProtocolFormatter": "processors.09_protocol_formatter",
}

def __getattr__(name: str):
    if name in _MODULE_MAP:
        module = importlib.import_module(_MODULE_MAP[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
