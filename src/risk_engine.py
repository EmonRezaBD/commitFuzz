import json
import re
import csv

# --- Metric Functions ---

def count_decision_points(code):
    """McCabe 1976 - count decision points"""
    keywords = r'\b(if|else|for|while|switch|case|catch)\b'
    operators = re.findall(r'(\&\&|\|\||\?)', code)
    keyword_matches = re.findall(keywords, code)
    return len(keyword_matches) + len(operators)

def cyclomatic_complexity_delta(entry):
    before_cc = count_decision_points(entry["Before_commit_codebase"])
    after_cc = count_decision_points(entry["After_commit_codebase"])
    return after_cc - before_cc

def control_flow_alteration(entry):
    """Nagappan & Ball 2005 - total disruption to control flow"""
    added = count_decision_points(entry["Only_addition_codes"])
    deleted = count_decision_points(entry["Only_deletion_codes"])
    return added + deleted

def change_size_ratio(entry):
    """Moser et al. 2008 - relative code churn"""
    added = len(entry["Only_addition_codes"].split("\n")) if entry["Only_addition_codes"] else 0
    deleted = len(entry["Only_deletion_codes"].split("\n")) if entry["Only_deletion_codes"] else 0
    before = len(entry["Before_commit_codebase"].split("\n")) if entry["Before_commit_codebase"] else 1
    return (added + deleted) / max(before, 1)

# --- Normalization ---

def normalize(values):
    """Min-max normalization to [0, 1]"""
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]

# --- Main Pipeline ---

def main():
    # Load all entries
    data = []
    with open("data/singleFuncDataset.jsonl") as f:
        for line in f:
            data.append(json.loads(line))
    
    print(f"Loaded {len(data)} entries")

    # Compute raw metrics for each entry
    cc_deltas = []
    flow_scores = []
    change_ratios = []

    for entry in data:
        cc_deltas.append(cyclomatic_complexity_delta(entry))
        flow_scores.append(control_flow_alteration(entry))
        change_ratios.append(change_size_ratio(entry))

    # Normalize
    norm_cc = normalize(cc_deltas)
    norm_flow = normalize(flow_scores)
    norm_ratio = normalize(change_ratios)

    # Compute final risk (equal weights)
    results = []
    for i, entry in enumerate(data):
        risk_score = 0.33 * norm_cc[i] + 0.33 * norm_flow[i] + 0.34 * norm_ratio[i]
        
        # Classify
        if risk_score < 0.3:  #tertile split
            level = "LOW"
        elif risk_score < 0.6:
            level = "MEDIUM"
        else:
            level = "HIGH"

        results.append({
            "commit_title": entry["Commit title"],
            "cc_delta": cc_deltas[i],
            "flow_score": flow_scores[i],
            "change_ratio": round(change_ratios[i], 3),
            "norm_cc": round(norm_cc[i], 3),
            "norm_flow": round(norm_flow[i], 3),
            "norm_ratio": round(norm_ratio[i], 3),
            "risk_score": round(risk_score, 3),
            "risk_level": level
        })

    # Save to CSV
    with open("results/risk_scores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Print summary
    levels = [r["risk_level"] for r in results]
    print(f"\nResults: LOW={levels.count('LOW')}, MEDIUM={levels.count('MEDIUM')}, HIGH={levels.count('HIGH')}")
    
    # Print top 5 riskiest
    print("\nTop 5 Riskiest Commits:")
    sorted_results = sorted(results, key=lambda x: x["risk_score"], reverse=True)
    for r in sorted_results[:5]:
        print(f"  [{r['risk_level']}] {r['risk_score']} - {r['commit_title'][:60]}")

if __name__ == "__main__":
    main()