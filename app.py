"""AI Resume ATS Checker: Streamlit UI + Gemini Flash."""

import json
import os

import streamlit as st
from docx import Document
from google import genai
from google.genai import types
from pypdf import PdfReader

# Change the model without editing code: set GEMINI_MODEL in secrets / env.
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODEL = "gemini-2.5-flash"
MAX_CHARS = 15000

PROMPT = """You are an expert ATS (Applicant Tracking System) and resume reviewer.
Analyze the resume below{jd_note} and reply with ONLY valid JSON in this exact shape:
{{
  "ats_score": <integer 0-100>,
  "section_scores": {{
    "formatting": <0-100>,
    "keywords": <0-100>,
    "experience": <0-100>,
    "skills": <0-100>,
    "education": <0-100>
  }},
  "strengths": ["short point", "..."],
  "improvements": [
    {{"issue": "what is wrong", "fix": "specific, actionable fix"}}
  ],
  "missing_keywords": ["keyword", "..."]
}}
Rules: be honest and strict, give 3-6 strengths and 5-8 improvements, and base
missing_keywords on {kw_source}.

RESUME:
{resume}
{jd_block}"""


# ---------- helpers ----------
def extract_text(file) -> str:
    """Read text from an uploaded PDF or DOCX."""
    name = file.name.lower()
    if name.endswith(".pdf"):
        return "\n".join(page.extract_text() or "" for page in PdfReader(file).pages)
    if name.endswith(".docx"):
        doc = Document(file)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
        return "\n".join(parts)
    raise ValueError("Unsupported file type. Please upload a PDF or DOCX.")


def parse_json(text: str) -> dict:
    """Parse model output, tolerating stray text or code fences."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("The AI did not return valid JSON. Please try again.")
        return json.loads(text[start : end + 1])


def clamp(value) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def analyze_resume(resume: str, job_desc: str, api_key: str) -> dict:
    """Send the resume to Gemini and return a cleaned result dict."""
    prompt = PROMPT.format(
        jd_note=" against the job description" if job_desc else "",
        kw_source="the job description" if job_desc else "common keywords for this role",
        resume=resume[:MAX_CHARS],
        jd_block=f"\nJOB DESCRIPTION:\n{job_desc[:MAX_CHARS]}" if job_desc else "",
    )
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=0.2, response_mime_type="application/json"
    )

    last_error = None
    for model in dict.fromkeys([PRIMARY_MODEL, FALLBACK_MODEL]):
        try:
            response = client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            data = parse_json(response.text or "")
            break
        except Exception as e:  # try the next model
            last_error = e
    else:
        raise RuntimeError(f"Gemini request failed: {last_error}")

    sections = data.get("section_scores") or {}
    return {
        "ats_score": clamp(data.get("ats_score")),
        "section_scores": {k: clamp(v) for k, v in sections.items()},
        "strengths": data.get("strengths") or [],
        "improvements": data.get("improvements") or [],
        "missing_keywords": data.get("missing_keywords") or [],
    }


def get_api_key() -> str:
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # no secrets file locally
        key = None
    return key or os.getenv("GEMINI_API_KEY") or st.sidebar.text_input(
        "Gemini API key", type="password", help="Get a free key at aistudio.google.com"
    )


# ---------- UI ----------
def show_results(result: dict):
    score = result["ats_score"]
    st.metric("ATS Score", f"{score}/100")
    st.progress(score / 100)
    if score >= 80:
        st.success("Strong resume. Only small tweaks needed.")
    elif score >= 60:
        st.warning("Decent resume, but there is clear room to improve.")
    else:
        st.error("Needs significant work to pass most ATS filters.")

    if result["section_scores"]:
        st.subheader("Section scores")
        for name, value in result["section_scores"].items():
            st.write(f"**{name.title()}**: {value}/100")
            st.progress(value / 100)

    if result["strengths"]:
        st.subheader("Strengths")
        for item in result["strengths"]:
            st.markdown(f"- {item}")

    if result["improvements"]:
        st.subheader("Improvements")
        for i, item in enumerate(result["improvements"], 1):
            if isinstance(item, dict):
                st.markdown(f"**{i}. {item.get('issue', '')}**")
                st.write(item.get("fix", ""))
            else:
                st.markdown(f"**{i}.** {item}")

    if result["missing_keywords"]:
        st.subheader("Missing keywords")
        st.write(", ".join(map(str, result["missing_keywords"])))


def main():
    st.set_page_config(page_title="Resume ATS Checker", page_icon="📄")
    st.title("📄 Resume ATS Checker")
    st.caption("Upload your resume to get an ATS score and tips to improve it.")

    api_key = get_api_key()
    file = st.file_uploader("Upload resume (PDF or DOCX)", type=["pdf", "docx"])
    job_desc = st.text_area(
        "Job description (optional, gives a more accurate score)", height=150
    )

    if not st.button("Analyze resume", type="primary"):
        return
    if not api_key:
        st.error("Please add your Gemini API key.")
        return
    if file is None:
        st.error("Please upload a resume first.")
        return

    try:
        with st.spinner("Reading your resume..."):
            resume = extract_text(file).strip()
        if len(resume) < 200:
            st.error(
                "Could not read enough text. Scanned or image-only PDFs are not "
                "supported. Please upload a text-based PDF or DOCX."
            )
            return
        with st.spinner("Analyzing with Gemini..."):
            result = analyze_resume(resume, job_desc.strip(), api_key)
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        return

    show_results(result)
    st.caption("Scores are AI estimates, not the output of a real ATS.")


if __name__ == "__main__":
    main()
