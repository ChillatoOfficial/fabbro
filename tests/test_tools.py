import os
import tempfile
import unittest

from fabbro import paths
from fabbro.core import rag
from fabbro.tools import discover_tools


def tool(nome):
    return {t.name: t for t in discover_tools(True)}[nome]


class FileTools(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.f = os.path.join(self.dir, "a.py")
        with open(self.f, "w") as fh:
            fh.write("x = 1\n")

    def test_modifica_richiede_lettura(self):
        r = tool("edit_file").run({"path": self.f, "old_string": "x = 1", "new_string": "x = 2"})
        self.assertIn("leggi prima", r)
        tool("read_file").run({"path": self.f})
        r = tool("edit_file").run({"path": self.f, "old_string": "x = 1", "new_string": "x = 2"})
        self.assertIn("modificato", r)
        with open(self.f) as fh:
            self.assertEqual(fh.read(), "x = 2\n")

    def test_old_string_ambiguo(self):
        with open(self.f, "w") as fh:
            fh.write("a\na\n")
        tool("read_file").run({"path": self.f})
        r = tool("edit_file").run({"path": self.f, "old_string": "a", "new_string": "b"})
        self.assertIn("2 volte", r)

    def test_bash(self):
        self.assertIn("ciao", tool("bash").run({"command": "echo ciao"}))
        self.assertIn("timeout", tool("bash").run({"command": "sleep 5", "timeout": 1}))


class CreateTool(unittest.TestCase):
    CODE = 'from agentecore import tool\n\n@tool\ndef ciao_test(n: str) -> str:\n    """Saluta.\n\n    Args:\n        n: nome\n    """\n    return "ciao " + n\n'

    def test_crea_e_rifiuta(self):
        ct = tool("create_tool")
        self.assertIn("creato", ct.run({"name": "ciao_test", "code": self.CODE}))
        self.assertEqual(tool("ciao_test").run({"n": "x"}), "ciao x")
        self.assertIn("integrato", ct.run({"name": "bash", "code": self.CODE}))
        self.assertIn("non si carica", ct.run({"name": "rotto_test", "code": "import nonesiste\n" + self.CODE}))
        self.assertFalse((paths.TOOLS / "rotto_test.py").exists())
        os.remove(paths.TOOLS / "ciao_test.py")


class Rag(unittest.TestCase):
    def test_cerca(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "g.md"), "w") as fh:
            fh.write("# Deploy\nesegui il deploy\n## Rollback\nusa make rollback per tornare indietro\n# DB\nmigrazioni con alembic\n")
        rag.aggiungi(d)
        ris = rag.cerca("rollback del deploy", 1)
        self.assertEqual(ris[0]["titolo"], "Deploy › Rollback")
        self.assertEqual(rag.cerca("zzzz"), [])
        rag.rimuovi("g.md")


if __name__ == "__main__":
    unittest.main()
