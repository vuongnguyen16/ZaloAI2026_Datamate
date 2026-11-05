"""Raw business ingestion. No cleaning, model execution or gold access."""

from datamate.ingest.loader import ingest_business, ingest_split
from datamate.ingest.model import IngestError, LoaderOptions

__all__ = ["IngestError", "LoaderOptions", "ingest_business", "ingest_split"]
