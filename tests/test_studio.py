import importlib.util
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import ascii_art_studio as studio

class ConversionTests(unittest.TestCase):
    def test_black_white_and_invert(self):
        image=Image.new('RGB',(2,1)); image.putpixel((1,0),(255,255,255))
        rows,_=studio.convert_image(image,width=2,ratio=1,ramp='# ')
        self.assertEqual(rows,['# '])
        rows,_=studio.convert_image(image,width=2,ratio=1,ramp='# ',invert=True)
        self.assertEqual(rows,[' #'])
    def test_alpha_composites_black(self):
        rows,_=studio.convert_image(Image.new('RGBA',(1,1),(255,255,255,0)),width=1,ramp='# ')
        self.assertEqual(rows,['#'])
    def test_invalid_inputs(self):
        for options in ({'width':0},{'ramp':''},{'ramp':'a\nb'},{'ratio':float('nan')}):
            with self.assertRaises(ValueError):studio.convert_image(Image.new('RGB',(2,2)),**options)
    def test_ansi_indices_valid_for_all_grays(self):
        for v in range(256):self.assertTrue(16<=studio.rgb_to_ansi256(v,v,v)<=255)
    def test_html_escapes_content(self):
        output=studio.make_html(['<&'],[[(255,0,0),(0,255,0)]])
        self.assertIn('&lt;',output); self.assertIn('&amp;',output)
    def test_png_character_cell_is_single_width(self):
        image=studio.render_ascii_image(['MMMM'],font_size=14)
        font=studio.load_font(14)
        import math
        self.assertEqual(image.width,math.ceil(font.getlength('M'))*4)
    def test_png_limit(self):
        with self.assertRaises(ValueError):studio.render_ascii_image(['x'*500]*500,font_size=88)
    def test_ansi_reset_each_line(self):
        output=studio.make_ansi(['a','b'],[[(255,0,0)],[(0,255,0)]],'TrueColor')
        self.assertEqual(output.count('\x1b[0m'),2)

class AppTests(unittest.TestCase):
    def test_async_conversion_views_and_clipboard(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(studio,'SETTINGS_PATH',str(Path(directory)/'settings.json')):
            app=studio.App(standalone=False)
            try:
                app.root.withdraw()
                app.img=Image.new('RGB',(80,60),(200,100,50))
                app.do_update()
                end=time.monotonic()+10
                while app._busy and time.monotonic()<end:
                    app.root.update(); time.sleep(.02)
                self.assertFalse(app._busy)
                self.assertTrue(app.rows)
                app._render_color(); app._render_text()
                app.copy_text()
                self.assertNotIn('\x1b',app.root.clipboard_get())
                for method, suffix in ((app.save_txt, '.txt'), (app.save_ans, '.ans'), (app.save_png, '.png'), (app.save_html, '.html')):
                    destination = Path(directory) / ('export' + suffix)
                    with patch.object(studio.filedialog, 'asksaveasfilename', return_value=str(destination)):
                        method()
                    self.assertGreater(destination.stat().st_size, 0)
                    if suffix == '.png':
                        with Image.open(destination) as output:
                            self.assertGreater(output.width, 0)
                with patch.object(studio.filedialog, 'asksaveasfilename', return_value=str(Path(directory)/'missing'/'out.txt')), patch.object(studio.messagebox, 'showerror') as error:
                    app.save_txt()
                    error.assert_called_once()
                project=Path(directory)/'roundtrip.asciiproject'
                with patch.object(studio.filedialog,'asksaveasfilename',return_value=str(project)):
                    app.save_project()
                app.var_width.set(40)
                with patch.object(studio.filedialog,'askopenfilename',return_value=str(project)):
                    app.open_project()
                self.assertEqual(app.var_width.get(),80)
                self.assertEqual(app.img.getpixel((0,0)),(200,100,50,255))
                import xml.etree.ElementTree as ET
                svg=studio.make_svg(['<&'],[[(255,0,0),(0,255,0)]])
                self.assertEqual(ET.fromstring(svg).tag,'{http://www.w3.org/2000/svg}svg')
                app.var_custom.delete(0,'end'); app.var_custom.insert(0,'\t')
                app.var_ramp.set('Özel'); app.do_update()
                end=time.monotonic()+10
                while app._busy and time.monotonic()<end:
                    app.root.update(); time.sleep(.02)
                self.assertEqual(app.rows,[])
            finally:app.on_close()

if __name__=='__main__':unittest.main()
