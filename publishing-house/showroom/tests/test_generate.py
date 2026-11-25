"""Exercise the rendered contract, not notebook execution or a mock exporter."""
import importlib.util
import json
import re
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

    def render_cells(self, *cells):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as temp:
            source = Path(temp) / 'module-01-example.ipynb'
            nbformat.write(nbformat.v4.new_notebook(cells=list(cells)), source)
            return self.generator.render(source)

    def test_guide_has_intro_steps_questions_done_diagrams_and_no_code(self):
        md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
        result = self.render_cells(
            md('# A lesson\n\n> **Prototype notebook.** draft\n\nWhat this module is about, with [config](../agent/config.toml) and [`tools.py`](../agent/tools.py).'),
            code('raise RuntimeError("must never execute")\n%cd ../agent'),
            md('## Start from module 1\n\nReset first.'),
            md('## 1. Run it\n\nSome step text.'),
            md('**Your read:** what happened?'),
            md('<details><summary>Check your answer</summary>\n\n1. First answer.\n2. Second answer.\n</details>'),
            md('## 2. Fix it\n\n```mermaid\nflowchart LR\n A --> B\n```'),
            md("**This is the module's success signal:** the run stops."),
            md('## If the result differs\n\nCheck the reset.'),
        )
        self.assertIn('= A lesson\n', result)
        self.assertIn('What this module is about', result)
        self.assertNotIn('Prototype notebook', result)
        # Repository links open the file in the participant's workbench, in a new tab.
        self.assertIn('link:{lab-workbench-url}/agent/config.toml[config^]', result)
        self.assertIn('link:{lab-workbench-url}/agent/tools.py[`+tools.py+`^]', result)
        self.assertNotIn('github.com', result)
        self.assertIn('[`+tools.py+`^]', result)
        self.assertIn("== What you'll do in the notebook", result)
        self.assertIn('. Run it\n. Fix it', result)
        self.assertNotIn('Start from module 1', result)
        self.assertIn('*Your read:* what happened?', result)
        self.assertIn('.Check your answer\n[%collapsible]', result)
        self.assertLess(result.index('First answer.'), result.index('Second answer.'))
        self.assertIn('== How you know it worked\n\nThe run stops.', result)
        self.assertIn('[mermaid]\n', result)
        self.assertLess(result.index('== Diagrams'), result.index('[mermaid]'))
        self.assertIn('== If the result differs', result)
        self.assertLess(result.index('== If the result differs'), result.index('Check the reset.'))
        self.assertIn('[%collapsible]\n====\n\nCheck the reset.', result)
        # The notebook holds the code; the guide never copies it.
        self.assertNotIn('RuntimeError', result)
        self.assertNotIn('[source,python]', result)
        self.assertNotIn('<details>', result)

    def test_unsafe_markdown_fails_instead_of_slipping_through(self):
        md = nbformat.v4.new_markdown_cell
        for cells, message in (
            ([md('# T'), md('## 1. Step'), md('<details><summary>A</summary>\n\nOrphan answer.\n</details>')],
             'must follow'),
            ([md('# T'), md('**Your read:** q?'), md('<details><summary>A</summary>\n\n```python\nx = 1\n```\n</details>')],
             'must not contain code'),
            ([md('# T'), md('~~~\ncode\n~~~')], 'plain ``` fences'),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_cells(*cells)

    def test_saved_outputs_are_never_published(self):
        cell = nbformat.v4.new_code_cell('print("run in JupyterLab")', execution_count=42)
        cell.outputs = [nbformat.v4.new_output('stream', name='stdout', text='PRIVATE_SAVED_OUTPUT')]
        result = self.render_cells(nbformat.v4.new_markdown_cell('# Title'), cell)
        self.assertNotIn('PRIVATE_SAVED_OUTPUT', result)
        self.assertNotIn('In[42]', result)

    def test_real_seven_modules_get_a_guide(self):
        sources = sorted((ROOT / 'notebooks').glob('module-*.ipynb'))
        self.assertEqual(len(sources), 7)
        for source in sources:
            with self.subTest(source=source.name):
                result = self.generator.render(source)
                self.assertIn(f"link:{{lab-workbench-url}}/notebooks/{source.name}[Open this module's notebook^]", result)
                self.assertIn(':lab-workbench-url: https://rh-ai.{openshift_cluster_ingress_domain}/notebook/{user}-app'
                              '/kestrel-agent/lab/tree/agent-antipatterns-lab\n', result)
                self.assertNotIn('github.com', result)
                cells = json.loads(source.read_text())['cells']
                heading = ''.join(cells[0]['source']).splitlines()[0]
                self.assertIn(heading.replace('# ', '= ', 1) + '\n', result)
                steps = [line for c in cells if c['cell_type'] == 'markdown'
                         for line in ''.join(c['source']).splitlines() if re.match(r'## \d+\. ', line)]
                for line in steps:
                    self.assertIn('. ' + line.split('. ', 1)[1].strip(), result)
                self.assertNotIn('[source,python]', result)
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
