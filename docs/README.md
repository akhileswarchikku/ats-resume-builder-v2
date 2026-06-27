# docs/

Place your personal documents here. These files are gitignored — never committed.

| File | Purpose |
|------|---------|
| `resume.docx` | Your master resume (DOCX). The parser reads formatting, hyperlinks, and tab stops directly from the XML — keep it well-structured. |
| `resume.pdf` | Optional PDF copy. Used as fallback for ATS text extraction. |
| `Project_Portfolio_Akhileswar.docx` | Project portfolio (or rename to `portfolio.docx`). The keyword extractor checks this for skill evidence. |

The API reads from `DOCS_DIR` (set in `.env`), which defaults to `./docs`.
