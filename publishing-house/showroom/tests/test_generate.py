"""Exercise the rendered contract, not notebook execution or a mock exporter."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import nbformat

DIRECTORY = Path(__file__).resolve().parents[1]
ROOT = DIRECTORY.parents[1]


class ShowroomMirrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("showroom_generate", DIRECTORY / "generate.py")
        cls.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generator)

    def test_mirror_keeps_order_code_diagrams_answers_and_links(self):
        notebook = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell('# A lesson\n\n## Read this\n\n[config](../agent/config.toml)'),
            nbformat.v4.new_code_cell('raise RuntimeError("must never execute")\n%cd ../agent\n!python agent.py'),
            nbformat.v4.new_markdown_cell('```mermaid\nflowchart LR\n A --> B\n```'),
            nbformat.v4.new_markdown_cell('<details><summary>Check your answer</summary>\n\n1. First answer.\n2. Second answer.\n</details>'),
        ])
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as temp:
            source = Path(temp) / 'module-01-example.ipynb'
            nbformat.write(notebook, source)
            result = self.generator.render(source)
        self.assertIn('= A lesson\n', result)
        self.assertIn('== Read this', result)
        self.assertIn('{lab-source-url}/agent/config.toml[config]', result)
        self.assertIn('[source,python]', result)
        self.assertIn('raise RuntimeError("must never execute")\n%cd ../agent\n!python agent.py', result)
        self.assertIn('[mermaid]\n', result)
        self.assertIn('flowchart LR\n A --> B', result)
        self.assertIn('.Check your answer\n[%collapsible]\n====', result)
        self.assertLess(result.index('First answer.'), result.index('Second answer.'))
        self.assertLess(result.index('== Read this'), result.index('raise RuntimeError'))
        self.assertLess(result.index('raise RuntimeError'), result.index('[mermaid]'))
        self.assertNotIn('<details>', result)

    def test_saved_outputs_are_never_published(self):
        cell = nbformat.v4.new_code_cell('print("run in JupyterLab")', execution_count=42)
        cell.outputs = [nbformat.v4.new_output('stream', name='stdout', text='PRIVATE_SAVED_OUTPUT')]
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as temp:
            source = Path(temp) / 'module-01-example.ipynb'
            nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# Title'), cell]), source)
            result = self.generator.render(source)
        self.assertNotIn('PRIVATE_SAVED_OUTPUT', result)
        self.assertNotIn('In[42]', result)
        self.assertIn('print("run in JupyterLab")', result)

    def test_real_seven_modules_include_every_code_cell_in_order(self):
        sources = sorted((ROOT / 'notebooks').glob('module-*.ipynb'))
        self.assertEqual(len(sources), 7)
        for source in sources:
            with self.subTest(source=source.name):
                result = self.generator.render(source)
                self.assertIn(f'/notebooks/{source.name}[', result)
                self.assertIn('Prototype notebook.', result)
                position = 0
                for cell in json.loads(source.read_text())['cells']:
                    if cell['cell_type'] == 'code' and ''.join(cell['source']).strip():
                        code = ''.join(cell['source']).rstrip()
                        position = result.index(code, position) + len(code)
                self.assertNotIn('link:../agent/', result)

    def test_check_detects_drift_and_does_not_write(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as temp:
            output = Path(temp)
            command = [sys.executable, str(DIRECTORY / 'generate.py'), '--output-dir', str(output)]
            generated = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            checked = subprocess.run([*command, '--check'], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            pages = sorted(output.glob('module-*.adoc'))
            self.assertEqual(len(pages), 7)
            pages[0].write_text('deliberately stale\n')
            pages[1].unlink()
            checked = subprocess.run([*command, '--check'], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 1)
            self.assertIn(pages[0].name, checked.stdout)
            self.assertIn(pages[1].name, checked.stdout)
            self.assertEqual(pages[0].read_text(), 'deliberately stale\n')
            self.assertFalse(pages[1].exists())


if __name__ == '__main__':
    unittest.main()
