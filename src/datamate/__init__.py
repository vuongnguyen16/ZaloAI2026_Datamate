"""DataMate. Real model execution belongs on Modal, never on this CPU harness."""

import time

# Captured before CLI imports/data/model initialization; not an OS birth timestamp.
APPLICATION_STARTED = time.monotonic()

__version__ = "0.1.0"
