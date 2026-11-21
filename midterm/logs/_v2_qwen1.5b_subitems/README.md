# Archived run v2: chunk per sub-item, Qwen2.5-1.5B-Instruct

**This is NOT the final result.** The final results (Qwen2.5-3B-Instruct) are in the parent folder `logs/`.

This run uses the same 778 sub-item chunks, the same 20 questions and the same 320 test cases as the final run. Only the generator differs (1.5B instead of 3B), and the short answer style was used.

The report uses this run for extension (5), "two generators". It reads `summary.csv` and `garak_summary.json` from this folder.
`manual_overrides.json` here belongs to this run: one regex false positive found by the student during the demo.
