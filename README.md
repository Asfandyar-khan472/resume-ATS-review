# 📄 ATS Resume Checker

Upload a resume (PDF, DOCX or TXT) and get an **ATS score**, a breakdown by category, and specific, prioritized improvements. Optionally paste a job description to get a tailored keyword match.

Built with **Streamlit** and the **Google Gemini API**.

## How the score works

| Part | Weight | Source |
|------|--------|--------|
| AI content score (keywords & relevance, content quality, impact, clarity) | 70% | Gemini |
| ATS structure score (contact info, standard sections, length, bullets, dates, quantified results) | 30% | Deterministic rules in `app.py` |

The score is an **estimate**. Real ATS products differ and none publishes an official score.

## Features

- Text extraction from PDF, DOCX (including tables) and TXT
- Prioritized improvements (high / medium / low) with concrete fixes
- Missing keywords and before/after rewrite examples
- Optional job-description matching
- Downloadable Markdown report
- Warns on scanned/image-only resumes that an ATS can't read

## Run locally

```bash
git clone https://github.com/<your-username>/ats-resume-checker.git
cd ats-resume-checker

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey), then create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key-here"
# Optional: override the default model
# GEMINI_MODEL = "gemini-3.5-flash"
```

Start the app:

```bash
streamlit run app.py
```

You can also skip the secrets file and paste the key into the sidebar, or set the `GEMINI_API_KEY` environment variable.

## Configuration

| Setting | Where | Default |
|---------|-------|---------|
| `GEMINI_API_KEY` | Streamlit secret or env var | none (required) |
| `GEMINI_MODEL` | Streamlit secret or env var, or sidebar | `gemini-3.5-flash` |
| `MAX_RUNS_PER_SESSION` | constant in `app.py` | 10 (when the server key is used) |

Gemini model names change over time. If you get a "model not found" error, set `GEMINI_MODEL` to a current Flash model listed in the [Gemini docs](https://ai.google.dev/gemini-api/docs/models).

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **Create app**, pick the repo, branch `main`, and main file `app.py`.
4. Open **Advanced settings**, choose Python 3.11 or 3.12, and paste into **Secrets**:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
5. Click **Deploy**.

## Privacy

The extracted resume text (and job description, if given) is sent to Google's Gemini API. Nothing is stored by this app, but check Google's terms for how API data is handled.

## Project structure

```
app.py             # Streamlit UI, extraction, rule checks, Gemini call
requirements.txt
README.md
```

## Limitations

- Image-only (scanned) PDFs can't be read; export a text-based PDF instead.
- Multi-column or heavily designed layouts can extract out of order, which is also a real ATS risk.
- AI feedback can be wrong. Only add keywords or numbers that are true for you.

