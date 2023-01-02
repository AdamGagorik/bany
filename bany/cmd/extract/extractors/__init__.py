from . import base
from . import pdf


EXTRACTORS: dict[str, type[base.Extractor]] = {
    "pdf": pdf.Extractor,
}
