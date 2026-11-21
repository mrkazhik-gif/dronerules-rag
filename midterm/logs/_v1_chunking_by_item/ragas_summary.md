# Ragas retrieval metrics (ID-based, Ragas 0.4.3)

Reference passages: official chunks of the cited item that contain the correct value (22 for 20 questions).

| Config | N poisoned | Context precision | Context recall |
|---|---|---|---|
| baseline | 0 | 0.18 | 0.85 |
| baseline | 1 | 0.18 | 0.85 |
| baseline | 3 | 0.17 | 0.80 |
| baseline | 5 | 0.00 | 0.00 |
| baseline_k10 | 0 | 0.10 | 0.88 |
| baseline_k10 | 1 | 0.10 | 0.88 |
| baseline_k10 | 3 | 0.09 | 0.85 |
| baseline_k10 | 5 | 0.09 | 0.85 |
| source_aware | 0 | 0.18 | 0.85 |
| source_aware | 1 | 0.18 | 0.85 |
| source_aware | 3 | 0.17 | 0.80 |
| source_aware | 5 | 0.00 | 0.00 |
| provenance | 0 | 0.18 | 0.85 |
| provenance | 1 | 0.18 | 0.85 |
| provenance | 3 | 0.18 | 0.85 |
| provenance | 5 | 0.18 | 0.85 |
