from bany.cmd.extract.extractors import base, pdf

EXTRACTORS: dict[str, type[base.Extractor]] = {
    "pdf": pdf.Extractor,
}
