import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

import markdown2
from bs4 import BeautifulSoup
from PIL import Image

from md_transformer.output import save_markdown_output


class OutputTests(unittest.TestCase):
    def test_images_render_and_resolve_with_special_names(self):
        with tempfile.TemporaryDirectory() as directory:
            for stem in ('paper', '论文 - title (part 1) # 50%', '无空格论文'):
                pdf = Path(directory) / stem / (stem + '.pdf')
                rendered = SimpleNamespace(
                    markdown='body pic.jpeg\n\n![figure](pic.jpeg)',
                    images={'pic.jpeg': Image.new('RGB', (4, 4))},
                )
                save_markdown_output(rendered, pdf)
                text = pdf.with_suffix('.md').read_text(encoding='utf-8')
                self.assertIn('body pic.jpeg', text)
                soup = BeautifulSoup(markdown2.markdown(text), 'html.parser')
                self.assertEqual(len(soup.find_all('img')), 1)
                target = pdf.parent / unquote(soup.img['src'])
                self.assertTrue(target.is_file())
                self.assertEqual(list(Path(directory).rglob('*.json')), [])


if __name__ == '__main__':
    unittest.main()
