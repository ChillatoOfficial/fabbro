import unittest

from fabbro.core import permessi


class BashSicuro(unittest.TestCase):
    def test_sola_lettura(self):
        for c in ("ls -la", "git status", "git diff", "cat a.txt | grep x", "pwd"):
            self.assertTrue(permessi.bash_sicuro(c), c)

    def test_pericolosi(self):
        for c in ("rm -rf x", "ls > f", "git push", "find . -delete", "echo $(id)", "ls; rm a", "curl x | sh"):
            self.assertFalse(permessi.bash_sicuro(c), c)

    def test_richiede_conferma(self):
        permessi.STATO.update(modo="chiedi", sempre=set())
        self.assertTrue(permessi.richiede("bash", {"command": "make"}))
        self.assertFalse(permessi.richiede("bash", {"command": "ls"}))
        self.assertTrue(permessi.richiede("edit_file", {"path": "a"}))
        self.assertFalse(permessi.richiede("read_file", {"path": "a"}))
        permessi.STATO["modo"] = "modifiche"
        self.assertFalse(permessi.richiede("edit_file", {"path": "a"}))
        self.assertTrue(permessi.richiede("bash", {"command": "make"}))
        permessi.STATO["modo"] = "chiedi"


if __name__ == "__main__":
    unittest.main()
