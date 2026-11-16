import ast
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from presentation_generation_claim_audit.audit import audit, evidence, match_paragraph
from presentation_generation_claim_audit import phrases
from presentation_generation_claim_audit.__main__ import main

EXPECTED_YES = ('presentation generation', 'generate presentation', 'generates presentation', 'generating presentation', 'generate presentations', 'generates presentations', 'generating presentations', 'create presentation', 'creates presentation', 'creating presentation', 'create presentations', 'creates presentations', 'creating presentations', 'export presentation', 'exports presentation', 'exporting presentation', 'export to presentation', 'exports to presentation', 'exporting to presentation', 'export as presentation', 'exports as presentation', 'exporting as presentation', 'presentation export', 'presentation exports', 'presentation exporter', 'presentation slide generation', 'generate presentation slide', 'generates presentation slide', 'generating presentation slide', 'generate presentation slides', 'create presentation slide', 'creates presentation slide', 'write presentation', 'writes presentation', 'writing presentation', 'save as presentation', 'saves as presentation', 'save to presentation', 'saves to presentation', 'presentation writer', 'presentation writing', 'build presentation', 'builds presentation', 'building presentation', 'generate pptx', 'generates pptx', 'generating pptx', 'create pptx', 'creates pptx', 'creating pptx')
EXPECTED_NO = ('no presentation generation', 'does not generate presentation', 'does not generate presentations', 'does not support presentation generation', 'without presentation generation', 'no presentation export', 'does not export presentation', 'does not export to presentation', 'does not create presentation', 'does not create presentations', 'no presentation writer', 'does not write presentation', 'does not save as presentation', 'no presentation slide generation', 'does not generate presentation slides', 'does not build presentation', 'does not generate pptx', 'does not create pptx', 'presentation generation not supported', 'no presentation generation support', 'without presentation export', 'does not support presentation export', 'no presentation exporter', 'does not generate presentation slide')
EXPECTED_GENERIC = ('generate_presentation', 'generate_presentations', 'create_presentation', 'create_presentations', 'export_presentation', 'export_to_presentation', 'export_as_presentation', 'write_presentation', 'save_presentation', 'save_as_presentation', 'build_presentation', 'render_presentation', 'make_presentation', 'generate_pptx', 'create_pptx', 'export_pptx', 'export_to_pptx', 'write_pptx', 'save_pptx', 'build_pptx', 'generate_pptx_presentation', 'create_pptx_presentation', 'export_pptx_presentation', 'write_pptx_presentation')

class AuditTests(unittest.TestCase):
    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text())
        parsed = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)}
        self.assertEqual(parsed['PRESENTATIONGENERATION'], EXPECTED_YES)
        self.assertEqual(parsed['NOPRESENTATIONGENERATION'], EXPECTED_NO)
        self.assertEqual(parsed['GENERIC_NAMES'], EXPECTED_GENERIC)
        self.assertEqual((len(set(EXPECTED_YES)), len(set(EXPECTED_NO)), len(set(EXPECTED_GENERIC))), (50,24,24))

    def repo(self, docs='generate presentation', files=None, args=()):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'README.md').write_text(docs)
            for path, source in (files or {}).items():
                f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(source)
            return audit(root), self.cli(['audit',d,*args])

    def cli(self,args):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code=main(args)
        return code,out.getvalue()

    def test_good(self):
        result,cli=self.repo(files={'app.py': 'from pptx import Presentation\np=Presentation();p.save("out.pptx")'})
        self.assertEqual(result['verdict'],'PASS');self.assertEqual(cli[0],0)

    def test_bad(self):
        result,cli=self.repo()
        self.assertEqual(cli[0],2);self.assertEqual(result['findings'][0]['rule'],'documented-presentation-generation-claim-false')
        self.assertEqual(result['findings'][0]['severity'],'HIGH')

    def test_denial(self):
        result,cli=self.repo('does not generate presentation',{'a.py':'x.create_pptx()'})
        self.assertEqual(cli[0],2);self.assertEqual(result['findings'][0]['rule'],'documented-no-presentation-generation-claim-false')

    def test_no_source_denial(self):
        self.assertEqual(self.repo('no presentation generation')[0]['verdict'],'PASS')

    def test_no_claim(self):
        self.assertEqual(self.repo('ordinary text')[0]['verdict'],'PASS')

    def test_test_only(self):
        for path in ['tests/a.py','test_app.py','app_test.py']:
            with self.subTest(path=path):
                result,cli=self.repo(files={path:'x.create_pptx()'})
                self.assertEqual(result['findings'][0]['severity'],'MEDIUM');self.assertEqual(cli[0],0)
                self.assertEqual(self.repo(files={path:'x.create_pptx()'},args=['--fail-on','medium'])[1][0],2)

    def test_excluded_paths(self):
        for folder in ['fixtures','docs','examples']:
            self.assertEqual(self.repo(files={folder+'/a.py':'x.create_pptx()'})[0]['findings'][0]['severity'],'HIGH')

    def test_fences_inline(self):
        for fence in ['```','~~~','   ```']:
            self.assertEqual(self.repo(fence+'\ngenerate presentation\n'+fence)[0]['verdict'],'PASS')
        self.assertEqual(self.repo('`generate presentation`')[1][0],2)

    def test_matching(self):
        for phrase in EXPECTED_YES:
            self.assertTrue(match_paragraph(phrase)[0])
        for phrase in EXPECTED_NO:
            self.assertEqual(match_paragraph(phrase),(False,True))
        self.assertEqual(match_paragraph("doesn't generate presentation"),(False,True))
        self.assertEqual(match_paragraph('GENERATE-PRESENTATION'),(True,False))
        self.assertEqual(match_paragraph('regenerate presentationsuffix'),(False,False))
        self.assertEqual(match_paragraph('no presentation generation; create pptx'),(True,True))

    def test_split_modules(self):
        self.assertEqual(self.repo(files={'a.py':'from pptx import Presentation\nPresentation()', 'b.py':'p.save("out.pptx")'})[1][0],2)

    def test_ignore(self):
        self.assertEqual(self.repo(files={'vendor/a.py':'x.create_pptx()'},args=['--ignore','vendor'])[1][0],2)

    def test_json(self):
        code,out=self.repo(args=['--json'])[1];data=json.loads(out)
        self.assertEqual(code,2);self.assertIn('verdict',data);self.assertIn('message',data['findings'][0])

    def test_usage(self):
        for args in [[],['audit','/nonexistent'],['audit','--fail-on','HIGH'],['audit','--ignore','a','b']]:
            self.assertEqual(self.cli(args)[0],1)

    def test_version_entry(self):
        self.assertEqual(self.cli(['--version']),(0,'0.1.0\n'))
        result=subprocess.run([sys.executable,'-m','presentation_generation_claim_audit','--version'],capture_output=True,text=True)
        self.assertEqual((result.returncode,result.stdout),(0,'0.1.0\n'))

    def test_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'README.md').write_text('generate presentation')
            (root/'fixtures').mkdir();(root/'fixtures/a.py').write_text('x.create_pptx()')
            (root/'link.py').symlink_to(root/'fixtures/a.py');(root/'linked').symlink_to(root/'fixtures',target_is_directory=True)
            self.assertFalse(audit(root)['production_evidence'])

    def test_route_00(self):
        self.assertEqual(evidence('from pptx import Presentation\nPresentation().save("x")'), True)

    def test_route_01(self):
        self.assertEqual(evidence('import pptx\npptx.Presentation();x.save("x")'), True)

    def test_route_02(self):
        self.assertEqual(evidence('import pptx as px\npx.Presentation();x.save("x")'), True)

    def test_route_03(self):
        self.assertEqual(evidence('from pptx import Presentation as Deck\nDeck("existing.pptx");x.save("x")'), True)

    def test_route_04(self):
        self.assertEqual(evidence('from pptx.api import Presentation\nPresentation();x.save("x")'), True)

    def test_route_05(self):
        self.assertEqual(evidence('import pptx.api as api\napi.Presentation();x.save("x")'), True)

    def test_route_06(self):
        self.assertEqual(evidence('import pptx.api\npptx.api.Presentation();x.save("x")'), True)

    def test_route_07(self):
        self.assertEqual(evidence('from pptx import api\napi.Presentation();x.save("x")'), True)

    def test_route_08(self):
        self.assertEqual(evidence('x.generate_presentation()'), True)

    def test_route_09(self):
        self.assertEqual(evidence('x.generate_presentations()'), True)

    def test_route_10(self):
        self.assertEqual(evidence('x.create_presentation()'), True)

    def test_route_11(self):
        self.assertEqual(evidence('x.create_presentations()'), True)

    def test_route_12(self):
        self.assertEqual(evidence('x.export_presentation()'), True)

    def test_route_13(self):
        self.assertEqual(evidence('x.export_to_presentation()'), True)

    def test_route_14(self):
        self.assertEqual(evidence('x.export_as_presentation()'), True)

    def test_route_15(self):
        self.assertEqual(evidence('x.write_presentation()'), True)

    def test_route_16(self):
        self.assertEqual(evidence('x.save_presentation()'), True)

    def test_route_17(self):
        self.assertEqual(evidence('x.save_as_presentation()'), True)

    def test_route_18(self):
        self.assertEqual(evidence('x.build_presentation()'), True)

    def test_route_19(self):
        self.assertEqual(evidence('x.render_presentation()'), True)

    def test_route_20(self):
        self.assertEqual(evidence('x.make_presentation()'), True)

    def test_route_21(self):
        self.assertEqual(evidence('x.generate_pptx()'), True)

    def test_route_22(self):
        self.assertEqual(evidence('x.create_pptx()'), True)

    def test_route_23(self):
        self.assertEqual(evidence('x.export_pptx()'), True)

    def test_route_24(self):
        self.assertEqual(evidence('x.export_to_pptx()'), True)

    def test_route_25(self):
        self.assertEqual(evidence('x.write_pptx()'), True)

    def test_route_26(self):
        self.assertEqual(evidence('x.save_pptx()'), True)

    def test_route_27(self):
        self.assertEqual(evidence('x.build_pptx()'), True)

    def test_route_28(self):
        self.assertEqual(evidence('x.generate_pptx_presentation()'), True)

    def test_route_29(self):
        self.assertEqual(evidence('x.create_pptx_presentation()'), True)

    def test_route_30(self):
        self.assertEqual(evidence('x.export_pptx_presentation()'), True)

    def test_route_31(self):
        self.assertEqual(evidence('x.write_pptx_presentation()'), True)

    def test_route_32(self):
        self.assertEqual(evidence('from helpers import generate_presentation as route\nroute()'), True)

    def test_route_33(self):
        self.assertEqual(evidence('from helpers import generate_presentations as route\nroute()'), True)

    def test_route_34(self):
        self.assertEqual(evidence('from helpers import create_presentation as route\nroute()'), True)

    def test_route_35(self):
        self.assertEqual(evidence('from helpers import create_presentations as route\nroute()'), True)

    def test_route_36(self):
        self.assertEqual(evidence('from helpers import export_presentation as route\nroute()'), True)

    def test_route_37(self):
        self.assertEqual(evidence('from helpers import export_to_presentation as route\nroute()'), True)

    def test_route_38(self):
        self.assertEqual(evidence('from helpers import export_as_presentation as route\nroute()'), True)

    def test_route_39(self):
        self.assertEqual(evidence('from helpers import write_presentation as route\nroute()'), True)

    def test_route_40(self):
        self.assertEqual(evidence('from helpers import save_presentation as route\nroute()'), True)

    def test_route_41(self):
        self.assertEqual(evidence('from helpers import save_as_presentation as route\nroute()'), True)

    def test_route_42(self):
        self.assertEqual(evidence('from helpers import build_presentation as route\nroute()'), True)

    def test_route_43(self):
        self.assertEqual(evidence('from helpers import render_presentation as route\nroute()'), True)

    def test_route_44(self):
        self.assertEqual(evidence('from helpers import make_presentation as route\nroute()'), True)

    def test_route_45(self):
        self.assertEqual(evidence('from helpers import generate_pptx as route\nroute()'), True)

    def test_route_46(self):
        self.assertEqual(evidence('from helpers import create_pptx as route\nroute()'), True)

    def test_route_47(self):
        self.assertEqual(evidence('from helpers import export_pptx as route\nroute()'), True)

    def test_route_48(self):
        self.assertEqual(evidence('from helpers import export_to_pptx as route\nroute()'), True)

    def test_route_49(self):
        self.assertEqual(evidence('from helpers import write_pptx as route\nroute()'), True)

    def test_route_50(self):
        self.assertEqual(evidence('from helpers import save_pptx as route\nroute()'), True)

    def test_route_51(self):
        self.assertEqual(evidence('from helpers import build_pptx as route\nroute()'), True)

    def test_route_52(self):
        self.assertEqual(evidence('from helpers import generate_pptx_presentation as route\nroute()'), True)

    def test_route_53(self):
        self.assertEqual(evidence('from helpers import create_pptx_presentation as route\nroute()'), True)

    def test_route_54(self):
        self.assertEqual(evidence('from helpers import export_pptx_presentation as route\nroute()'), True)

    def test_route_55(self):
        self.assertEqual(evidence('from helpers import write_pptx_presentation as route\nroute()'), True)

    def test_rejection_00(self):
        self.assertEqual(evidence('import pptx'), False)

    def test_rejection_01(self):
        self.assertEqual(evidence('from pptx import Presentation\nPresentation()'), False)

    def test_rejection_02(self):
        self.assertEqual(evidence('from pptx import Presentation\nPresentation("deck.pptx")'), False)

    def test_rejection_03(self):
        self.assertEqual(evidence('import aspose.slides as slides\nslides.Presentation().save("x")'), False)

    def test_rejection_04(self):
        self.assertEqual(evidence('import spire.presentation\nspire.presentation.Presentation().SaveToFile("x")'), False)

    def test_rejection_05(self):
        self.assertEqual(evidence('import subprocess\nsubprocess.run(["libreoffice"])'), False)

    def test_rejection_06(self):
        self.assertEqual(evidence('import subprocess\nsubprocess.run(["soffice"])'), False)

    def test_rejection_07(self):
        self.assertEqual(evidence('subprocess.run(["pandoc"])'), False)

    def test_rejection_08(self):
        self.assertEqual(evidence('uno.open("x")'), False)

    def test_rejection_09(self):
        self.assertEqual(evidence('open("out.txt","w").write("x")'), False)

    def test_rejection_10(self):
        self.assertEqual(evidence('Path("x.md").write_text("x")'), False)

    def test_rejection_11(self):
        self.assertEqual(evidence('Image.save("x.png")'), False)

    def test_rejection_12(self):
        self.assertEqual(evidence('Canvas("x.pdf").save()'), False)

    def test_rejection_13(self):
        self.assertEqual(evidence('FPDF().output("x.pdf")'), False)

    def test_rejection_14(self):
        self.assertEqual(evidence('HTML().write_pdf("x.pdf")'), False)

    def test_rejection_15(self):
        self.assertEqual(evidence('PdfWriter().write("x.pdf")'), False)

    def test_rejection_16(self):
        self.assertEqual(evidence('Workbook().save("x.xlsx")'), False)

    def test_rejection_17(self):
        self.assertEqual(evidence('xlsxwriter.Workbook("x.xlsx").close()'), False)

    def test_rejection_18(self):
        self.assertEqual(evidence('DataFrame().to_excel("x.xlsx")'), False)

    def test_rejection_19(self):
        self.assertEqual(evidence('from docx import Document\nDocument().save("x.docx")'), False)

    def test_rejection_20(self):
        self.assertEqual(evidence('"presentation pptx slide"'), False)

    def test_rejection_21(self):
        self.assertEqual(evidence('client.parse(InvoiceV4)'), False)

    def test_rejection_22(self):
        self.assertEqual(evidence('client.begin_analyze_document("prebuilt-layout")'), False)

    def test_rejection_23(self):
        self.assertEqual(evidence('veryfi.Client()'), False)

    def test_rejection_24(self):
        self.assertEqual(evidence('documentai.process_document()'), False)

    def test_rejection_25(self):
        self.assertEqual(evidence('textract.analyze_document()'), False)

    def test_rejection_26(self):
        self.assertEqual(evidence('eden.universal_ai()'), False)

    def test_rejection_27(self):
        self.assertEqual(evidence('LlamaParse().load_data("x")'), False)

    def test_rejection_28(self):
        self.assertEqual(evidence('nanonets.OCR(model_id="opaque")'), False)

    def test_rejection_29(self):
        self.assertEqual(evidence('docsumo.upload("x")'), False)

    def test_rejection_30(self):
        self.assertEqual(evidence('abbyy.process("opaque")'), False)

    def test_rejection_31(self):
        self.assertEqual(evidence('rossum.upload("opaque")'), False)

    def test_rejection_32(self):
        self.assertEqual(evidence('klippa.parse("opaque")'), False)

    def test_rejection_33(self):
        self.assertEqual(evidence('parseur.upload("opaque")'), False)

    def test_rejection_34(self):
        self.assertEqual(evidence('extend.process("opaque")'), False)

    def test_rejection_35(self):
        self.assertEqual(evidence('generate_presentation()'), False)

    def test_rejection_36(self):
        self.assertEqual(evidence('from helper import generate_presentation\ndef generate_presentation(): pass\ngenerate_presentation()'), False)

    def test_rejection_37(self):
        self.assertEqual(evidence('def create_pptx(): pass\nx.create_pptx()'), False)

    def test_rejection_38(self):
        self.assertEqual(evidence('from pptx import Presentation\nclass Presentation: pass\nPresentation();x.save("x")'), False)

    def test_rejection_39(self):
        self.assertEqual(evidence('import pptx\npptx=other\npptx.Presentation();x.save("x")'), False)

    def test_rejection_40(self):
        self.assertEqual(evidence('import pptx\npptx: object = other\npptx.Presentation();x.save("x")'), False)

    def test_rejection_41(self):
        self.assertEqual(evidence('import pptx\nwith context() as pptx:\n pptx.Presentation();x.save("x")'), False)

    def test_rejection_42(self):
        self.assertEqual(evidence('from helpers import create_pptx\ncreate_pptx=other\ncreate_pptx()'), False)

    def test_rejection_43(self):
        self.assertEqual(evidence('not valid syntax !'), False)

    def test_rejection_44(self):
        self.assertEqual(evidence('from helpers import create_pptx\nclass C:\n def create_pptx(self): pass\ncreate_pptx()'), False)

    def test_readme_self_audit(self):
        from presentation_generation_claim_audit.audit import paragraphs
        for paragraph in paragraphs((Path(__file__).parents[1]/'README.md').read_text()):
            self.assertEqual(match_paragraph(paragraph), (False, False))

    def test_nested_docs(self):
        result,cli=self.repo('ordinary', {'nested/docs/features.md':'generate presentation'})
        self.assertEqual(cli[0],2)
        self.assertEqual(result['claims'],['nested/docs/features.md'])

    def test_two_findings(self):
        result,cli=self.repo('generate presentation\n\nno presentation generation',{'a.py':'x.create_pptx()'})
        self.assertEqual(len(result['findings']),1)
        self.assertEqual(result['findings'][0]['rule'],'documented-no-presentation-generation-claim-false')

    def test_ignore_repeatable(self):
        result,cli=self.repo(files={'vendor/a.py':'x.create_pptx()','generated/b.py':'x.create_pptx()'},args=['--ignore','vendor','--ignore','generated'])
        self.assertEqual(cli[0],2)

    def test_module_scoped_save(self):
        self.assertTrue(evidence('from pptx import Presentation\nPresentation()\ndef other():\n unrelated.save("anything")'))

    def test_nested_test_folder(self):
        result,cli=self.repo(files={'src/tests/test_app.py':'x.create_pptx()'})
        self.assertEqual(result['production_evidence'],[])
        self.assertEqual(result['test_evidence'],['src/tests/test_app.py'])

    def test_async_with_binding(self):
        self.assertFalse(evidence('import pptx\nasync def f():\n async with context() as pptx:\n  pptx.Presentation();x.save("x")'))

    def test_aliased_module_generic(self):
        self.assertTrue(evidence('import helpers.generate_presentation as route\nroute()'))

    def test_presentation_method_shadow(self):
        self.assertFalse(evidence('import pptx\nclass Other:\n def Presentation(self): pass\npptx.Presentation();x.save("x")'))

    def test_annotated_import_shadow(self):
        self.assertFalse(evidence('from helper import create_pptx as route\nroute: object = replacement\nroute()'))

    def test_with_import_shadow(self):
        self.assertFalse(evidence('from helper import create_pptx as route\nwith context() as route:\n route()'))

    def test_name_reference(self):
        self.assertFalse(evidence('from helper import create_pptx\ncreate_pptx'))

    def test_no_source_positive(self):
        result,cli=self.repo('presentation generation')
        self.assertEqual(cli[0],2)
        self.assertEqual(result['findings'][0]['severity'],'HIGH')
