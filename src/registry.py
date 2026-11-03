"""Local, standard-library registry validation and agent selection. No Meta API calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "faith_agent_registry.json"

def load_registry(path=REGISTRY_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    agents = data.get("agents", [])
    sectors = {entry["id"] for entry in data.get("sectors", [])}
    ids = [agent["id"] for agent in agents]
    if not agents or len(ids) != len(set(ids)):
        raise ValueError("Agent list must be nonempty with unique IDs")
    if not sectors:
        raise ValueError("At least one sector is required")
    if any(not set(agent["sectors"]).issubset(sectors) for agent in agents):
        raise ValueError("Agent refers to an unknown sector")
    if "scientific_critic" not in ids:
        raise ValueError("An independent scientific critic is required")
    if data.get("evidence_contract", {}).get("default_policy") != "ABSTAIN_ON_MISSING_EVIDENCE":
        raise ValueError("Scientific abstention default must be preserved")
    return data

def select_agents(sector, registry=None):
    registry = registry or load_registry()
    if sector not in {s["id"] for s in registry["sectors"]}:
        raise ValueError("Unknown FAITH sector: " + sector)
    return [a for a in registry["agents"] if sector in a["sectors"]]

if __name__ == "__main__":
    data = load_registry()
    selection = select_agents("mining", data)
    print(json.dumps({"pilot": data["pilot"], "selected_agent_ids": [a["id"] for a in selection], "meta_api_calls": 0}, ensure_ascii=False, indent=2))
