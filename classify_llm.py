import json
import re
from pathlib import Path
import requests

DATA_FILE = Path("tanitjobs_data.json")
MODEL = "llama3.1:8b"
DEBUG_LOG = Path("classify_llm_debug.log")
OLLAMA_API = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """You are a strict job classifier.
Return ONE single-line JSON object exactly like:
{"is_cs": true, "category": "software"}
Allowed categories: software, data, devops, it, other.
Consider CS-related if it is software engineering, data (AI/ML/BI/analytics), DevOps/SRE/platform, or IT/infra/support/security/cloud.
Non-CS examples: construction, retail, logistics, HR, finance, medical, education, sales, call centers, accounting, warehouse, electrician, chantier, plumbing, pharma, agriculture, retail store roles.
If unsure, respond with {"is_cs": false, "category": "other"}.
No code fences, no prose, no newlines, no extra fields."""
FEW_SHOTS = """
Title: Software Engineer (Backend)
Description: Building REST APIs in Python/Django and deploying to AWS.
Classify: {"is_cs": true, "category": "software"}

Title: Data Scientist
Description: Machine learning, NLP, feature engineering, model deployment.
Classify: {"is_cs": true, "category": "data"}

Title: DevOps / SRE Engineer
Description: Kubernetes, Docker, Terraform, CI/CD pipelines, observability.
Classify: {"is_cs": true, "category": "devops"}

Title: IT Support Specialist
Description: Helpdesk, network troubleshooting, Active Directory, security hardening.
Classify: {"is_cs": true, "category": "it"}

Title: Chef de chantier en électricité industrielle
Description: Superviser des équipes sur chantier, installations électriques industrielles.
Classify: {"is_cs": false, "category": "other"}

Title: Responsable de magasin
Description: Gestion des stocks, vente en boutique, encaissement.
Classify: {"is_cs": false, "category": "other"}

Title: Comptable
Description: Tenue de la comptabilité, facturation, fiscalité.
Classify: {"is_cs": false, "category": "other"}
"""

SYSTEM_PROMPT = """You are a strict job classifier for CS roles.
Output exactly ONE single-line JSON object like: {"is_cs": true, "category": "software"}
Allowed categories: software, data, devops, it, other.
CS-related means: software engineering, data (AI/ML/BI/analytics), DevOps/SRE/platform, IT/infra/support/security/cloud.
Non-CS: construction, retail, logistics, HR, finance, medical, education (non-IT), sales, call center, accounting, warehouse, electrician/chantier/plumbing, pharma, agriculture, retail store.
If unsure, reply {"is_cs": false, "category": "other"}.
No code fences, no prose, no extra fields.

Few-shot examples:
""" + FEW_SHOTS

def classify(title, desc):
    user_prompt = f"Title: {title}\nDescription: {desc}\nClassify:"
    prompt = SYSTEM_PROMPT + "\n" + user_prompt

    try:
        response = requests.post(
            OLLAMA_API,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "top_k": 20,
                    "num_predict": 96
                }
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()["response"].strip()
    except Exception as exc:
        with DEBUG_LOG.open("a", encoding="utf-8") as log:
            log.write(f"API error: {exc}\n---\n")
        return False, "other"

    # Try direct JSON parse
    for candidate in [result]:
        try:
            parsed = json.loads(candidate)
            return bool(parsed.get("is_cs", False)), parsed.get("category", "other")
        except Exception:
            pass

    # Log unexpected output to help debug
    with DEBUG_LOG.open("a", encoding="utf-8") as log:
        log.write(f"Raw response: {result}\n---\n")

    # Fallback: extract first JSON-looking object
    match = re.search(r"\{.*?\}", result)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return bool(parsed.get("is_cs", False)), parsed.get("category", "other")
        except Exception:
            pass

    # Last-resort heuristic if model output is unusable
    text = f"{title} {desc}".lower()
    cs_hits = any(w in text for w in [
        "software", "developer", "developpeur", "ingénieur", "ingenieur",
        "data", "ml", "ai", "ia", "analytics", "devops", "sre",
        "kubernetes", "docker", "cloud", "aws", "azure", "gcp",
        "python", "java", "javascript", "sql", "api", "it", "informatique"
    ])
    return (cs_hits, "software" if cs_hits else "other")

def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    for job in data:
        title = job.get("title", "") or ""
        desc = job.get("description", "") or ""
        is_cs, category = classify(title, desc)
        job["is_cs"] = is_cs
        job["cs_category"] = category
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Done: classified with LLM.")

if __name__ == "__main__":
    main()