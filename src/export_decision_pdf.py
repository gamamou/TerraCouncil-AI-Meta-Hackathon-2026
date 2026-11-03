"""HACK-009: session-bound, evidence-checked scientific deliberation PDF.

Only accepts a previously saved HACK-008 trace; never calls Meta or TTS.
Requires reportlab: python -m pip install reportlab.
All findings are checked against the same FSDC screened evidence.
"""
import argparse
import json
from pathlib import Path
import re
import sys

from verified_council import prepare
from verification import verify_submission

EXPECTED_ROLES = ["mining_industry", "environment_climate", "scientific_critic", "final_synthesis"]
REQUIRED_TRACE_STATUS = "COMPLETED_STRUCTURALLY_CHECKED_HUMAN_REVIEW_REQUIRED"

def _back_to_model(publication):
    return {
        "observations": [{"evidence_id": v["evidence_id"], "finding": v["finding"]}
                         for v in publication["observations"]],
        "hypotheses": [v["text"] for v in publication["hypotheses"]],
        "investigations": [v["text"] for v in publication["investigations"]],
        "abstentions": [v["text"] for v in publication["abstentions"]]
    }

def validate_session(trace, evidence):
    if trace.get("status") != REQUIRED_TRACE_STATUS or trace.get("human_review_required") is not True:
        raise ValueError("Incomplete, unverified, or missing human-review session")
    question = trace.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Missing question")
    job = prepare(question, evidence, "mining", "Boké, Guinea")
    source = job["gate"]
    if trace.get("evidence_sha256") != source["evidence_sha256"]:
        raise ValueError("FSDC evidence fingerprint mismatch")
    steps = trace.get("steps")
    if not isinstance(steps, list) or len(steps) != 4:
        raise ValueError("Expected exactly four verified HACK-008 stages")
    expected_models = ["muse-spark-1.3", "muse-spark-1.3",
                       "muse-wonder-1.0", "muse-spark-1.3"]
    for index, (step, role, model) in enumerate(zip(steps, EXPECTED_ROLES, expected_models)):
        if step.get("role") != role or step.get("model") != model:
            raise ValueError("Unrecognized model stage or role")
        if step.get("status") != "ACCEPTED_STRUCTURAL_ONLY":
            raise ValueError("Stage " + str(index) + " did not pass structural gate")
        publication = step.get("checked_publication")
        if not isinstance(publication, dict):
            raise ValueError("Missing verified stage publication")
        checked = verify_submission(_back_to_model(publication),
                                    source["evidence"], source["evidence_sha256"])
        if not checked["verified"]:
            raise ValueError("Stage " + str(index) + " source verification failed")
    if trace.get("decision_support") != steps[-1]["checked_publication"]:
        raise ValueError("Decision synthesis differs from final verified stage")
    return {"question": question, "evidence": source["evidence"],
            "sha256": source["evidence_sha256"], "steps": steps,
            "run_id": trace.get("run_id", "local"), "status": trace["status"]}

def export_pdf(data, output):
    try:
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, KeepTogether, PageBreak)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib import colors
        from reportlab.lib.units import mm
    except ImportError:
        raise RuntimeError("reportlab missing. Install: python -m pip install reportlab") from None
    from xml.sax.saxutils import escape
    output = Path(output)
    if output.exists():
        raise ValueError("PDF exists; choose a unique filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TCBody", parent=styles["BodyText"],
                              fontSize=9.5, leading=14, spaceAfter=7))
    styles.add(ParagraphStyle(name="TCMeta", parent=styles["Normal"],
                              textColor=colors.HexColor("#48566A"), fontSize=8, leading=11))
    styles.add(ParagraphStyle(name="TCSection", parent=styles["Heading2"],
                              textColor=colors.HexColor("#173F58"), spaceBefore=13))
    styles.add(ParagraphStyle(name="TCSub", parent=styles["Heading3"],
                              textColor=colors.HexColor("#1D526B"), spaceBefore=8))
    out = []
    def para(text, style="TCBody"):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])
    out.append(para("TerraCouncil AI — Scientific Decision Brief", "Title"))
    out.append(para("SustainAfrica / FAITH / FSDC · Meta Hackathon 2026", "TCMeta"))
    out.append(Spacer(1, 6 * mm))
    out.append(para("ANALYSE EXPLORATOIRE — DONNÉES NON VALIDÉES SUR LE TERRAIN", "TCSection"))
    out.append(para("Ce dossier reprend une délibération réelle de modèles Meta. Les contrôles structurels "
                    "n'établissent pas la vérité scientifique, la causalité, un accord de parties prenantes ou une autorisation d'investissement. "
                    "Une revue scientifique humaine reste obligatoire."))
    out.append(para("Question décisionnelle", "TCSection"))
    out.append(para(data["question"]))
    out.append(para("Session : " + str(data["run_id"]) + " · Source SHA-256 : " + data["sha256"], "TCMeta"))
    out.append(para("Sources FSDC examinées", "TCSection"))
    for e in data["evidence"]:
        out.append(para(e["evidence_id"] + " — " + e["dataset"], "TCSub"))
        out.append(para(e["finding"]))
        out.append(para("Statut : " + e["validation_status"] + " · " + e["source"] +
                        " · Année/date : " + e["observed_at"] + " · Méthode : " + e["method"], "TCMeta"))
    titles = ["1. Analyse minière — Muse Spark",
              "2. Perspective environnementale — Muse Spark",
              "3. Critique scientifique — Muse Wonder",
              "4. Synthèse révisée — Muse Spark"]
    for title, step in zip(titles, data["steps"]):
        out.append(para(title, "TCSection"))
        pub = step["checked_publication"]
        for key, heading in (("observations","Observations sourcées"),
                             ("hypotheses","Hypothèses non vérifiées"),
                             ("investigations","Investigations proposées"),
                             ("abstentions","Abstentions scientifiques")):
            out.append(para(heading, "TCSub"))
            entries = pub.get(key, [])
            if not entries:
                out.append(para("Aucun élément indiqué."))
            for item in entries:
                text = item["finding"] + " [" + item["evidence_id"] + "]" if key == "observations" else item["text"]
                out.append(para("• " + text))
    out.append(para("Conclusion et responsabilité", "TCSection"))
    out.append(para("Ces informations orientent les investigations et ne constituent pas une décision d'investir, "
                    "une étude d'impact réglementaire, une validation terrain ou une recommandation scientifique approuvée."))
    doc = SimpleDocTemplate(str(output), pagesize=(210*mm, 297*mm),
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=17*mm, bottomMargin=17*mm,
                            title="TerraCouncil — Scientific Decision Brief",
                            author="SustainAfrica — TerraCouncil")
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#607081"))
        canvas.drawString(18*mm, 11*mm, "TerraCouncil · Exploratoire · Revue humaine requise")
        canvas.drawRightString(192*mm, 11*mm, f"Page {document.page}")
        canvas.restoreState()
    doc.build(out, onFirstPage=footer, onLaterPages=footer)
    return output

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--session", required=True)
    a.add_argument("--evidence", required=True)
    a.add_argument("--out", required=True)
    args = a.parse_args()
    trace = json.loads(Path(args.session).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    data = validate_session(trace, evidence)
    print("SCIENTIFIC_STATUS: SCREENED_NOT_FIELD_VALIDATED")
    print("VERIFICATION: STRUCTURAL_ONLY")
    print("MODEL_CALLS: 0")
    print("PDF:", export_pdf(data, args.out))

if __name__ == "__main__":
    try: main()
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        print("STOP:", str(e), file=sys.stderr)
        sys.exit(2)
