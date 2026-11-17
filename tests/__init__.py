import os
import tempfile

# Cartella globale isolata: i test non toccano ~/.fabbro.
os.environ["FABBRO_HOME"] = tempfile.mkdtemp(prefix="fabbro-test-")
