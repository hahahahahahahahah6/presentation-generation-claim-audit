# Documentation claim auditor

An offline static auditor comparing documentation promises with listed source patterns. It reads root README.md and Markdown files under any docs path component. Source is parsed with the standard library and never executed. Audits perform no network access, telemetry or writes.

## Usage

```sh
PIP_NO_INDEX=1 python3 -m pip install --no-index --find-links local-wheelhouse .
presentation-generation-claim-audit audit . --json
python3 -m presentation_generation_claim_audit audit . --verbose
presentation-generation-claim-audit audit . --fail-on medium --ignore vendor --ignore generated
presentation-generation-claim-audit --version
```

The audit subcommand defaults to the current directory. Each ignore accepts one relative path prefix and can be repeated. Prefixes are lexical, relative to the root. The default threshold is high; medium also fails on test-only findings. Exit codes are 0 for PASS, 2 for findings meeting the threshold, and 1 for usage or I/O errors. PASS may contain medium findings. JSON includes verdict, findings (rule, severity, message, locations), production_evidence, test_evidence, claims and denials.

```text
documented-presentation-generation-claim-false HIGH (MEDIUM when evidence is test-only)
documented-no-presentation-generation-claim-false HIGH
```

## Matching

Blank lines delimit paragraphs. Backtick and tilde fences with up to three leading spaces are excluded; inline code counts. Text is lowercased, contractions expanded, hyphens replaced with spaces and whitespace collapsed. Exact phrases match at word boundaries, longest first with alphabetical ties. Denial spans are removed before positive matching. Each family produces at most one finding.

Imports and aliases resolve. Local functions, methods and classes shadow route names. Assignments, annotated assignments and context-manager bindings shadow imported names. Syntax-invalid files and symlinks provide no evidence. Files under fixtures, docs and examples are excluded; tests are tracked separately. A positive statement without source fails; a denial without source passes.

## Evidence and vocabulary

The checked operation produces .pptx files from code or data, including slides, text, shapes and images. The exact accepted vocabulary and generic calls follow.

```text
presentation generation
generate presentation
generates presentation
generating presentation
generate presentations
generates presentations
generating presentations
create presentation
creates presentation
creating presentation
create presentations
creates presentations
creating presentations
export presentation
exports presentation
exporting presentation
export to presentation
exports to presentation
exporting to presentation
export as presentation
exports as presentation
exporting as presentation
presentation export
presentation exports
presentation exporter
presentation slide generation
generate presentation slide
generates presentation slide
generating presentation slide
generate presentation slides
create presentation slide
creates presentation slide
write presentation
writes presentation
writing presentation
save as presentation
saves as presentation
save to presentation
saves to presentation
presentation writer
presentation writing
build presentation
builds presentation
building presentation
generate pptx
generates pptx
generating pptx
create pptx
creates pptx
creating pptx

no presentation generation
does not generate presentation
does not generate presentations
does not support presentation generation
without presentation generation
no presentation export
does not export presentation
does not export to presentation
does not create presentation
does not create presentations
no presentation writer
does not write presentation
does not save as presentation
no presentation slide generation
does not generate presentation slides
does not build presentation
does not generate pptx
does not create pptx
presentation generation not supported
no presentation generation support
without presentation export
does not support presentation export
no presentation exporter
does not generate presentation slide

generate_presentation
generate_presentations
create_presentation
create_presentations
export_presentation
export_to_presentation
export_as_presentation
write_presentation
save_presentation
save_as_presentation
build_presentation
render_presentation
make_presentation
generate_pptx
create_pptx
export_pptx
export_to_pptx
write_pptx
save_pptx
build_pptx
generate_pptx_presentation
create_pptx_presentation
export_pptx_presentation
write_pptx_presentation
```

The library route requires both a constructor and an attribute call named save in the same module. The write call is module scoped: it need not belong to the constructed object. Supported import forms include direct, aliased and attribute access. Generic calls count on any attribute base, or as an imported name; an unimported bare name does not count.

```py
from pptx import Presentation
p = Presentation()
p.save("deck.pptx")
```

## Limitations

This is static pattern matching, not semantic judgment. Dead code counts. Alias chains the tracer cannot follow are missed. Exact wording is required and denial handling depends on the listed vocabulary. Each route must occur in one module; split-module pairs do not count.

The checked wording may describe an empty shell, a menu download of an existing file, slides delivered by another service, a GUI save option, a reader wrapper or a person's job title, or a build step assembling existing parts. These can produce false positives: the auditor flags the wording and checks only the listed source patterns.

A constructor without a save call is not detected. Opening an existing file without saving is reading and is not detected. Bare imports, strings, filenames and comments do not count. The following alternatives are not detected:

```text
python-pptx Presentation without .save()
python-pptx Presentation("existing.pptx") without .save()
aspose-slides Presentation + .save(): commercial library, not a listed route; wheel not inspected
spire.presentation calls: commercial library, not a listed route; wheel not inspected
LibreOffice / UNO / pandoc subprocess: external binary invocation is not evidence
.txt / .html / .md / image writes: not the checked output format
reportlab / fpdf / WeasyPrint / pypdf PDF writes: another output format
openpyxl / xlsxwriter / pandas to_excel: another output format
python-docx Document + .save(): another output format
Mindee parse with any product: document extraction, not a writer
Azure begin_analyze_document with any model id: document reading
Veryfi calls of any kind: field extraction
Google Document AI process_document / batch_process_documents with any processor: reading
Eden AI universal-ai with any model id: no listed writer model
Textract calls of any kind: document reading
LlamaParse: document parsing
Nanonets / Docsumo / ABBYY Vantage / Rossum / Klippa / Parseur / Extend:
  extraction-side opaque model, skill, queue, template or workflow IDs,
  or generic upload endpoints configured outside the call
Raw OOXML / ZIP XML assembly of .pptx bytes: no listed call
```

Claims about PDF, spreadsheet or Word output are outside the vocabulary. So are extraction claims about invoices, receipts, identity documents, passports, checks, statements, tax forms, pay stubs, insurance cards, business cards, credit cards, contracts, mortgages, resumes, bills of lading, delivery notes, vehicle registrations, energy bills, marriage certificates, account details, nutrition labels, material certificates, mail, French health cards, Indian passports, driver licenses and vaccination cards. Invoice splitting, multiple receipt detection and document cropping are also outside scope.

## Development

Requires only the standard library at runtime. Build dependencies must be supplied locally for offline packaging.

```sh
python3 -m unittest discover
PIP_NO_INDEX=1 PIP_FIND_LINKS="$PWD/local-wheelhouse" python3 -m build
```

Licensed under MIT; see LICENSE.
