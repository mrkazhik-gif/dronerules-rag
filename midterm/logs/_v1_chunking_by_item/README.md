# Archived run v1: one chunk per item, Qwen2.5-1.5B-Instruct

**This is NOT the final result.** The final results (Qwen2.5-3B-Instruct) are in the parent folder `logs/`.

This first version kept each item of the rules as one chunk (420 chunks). Clean accuracy was only 75 %, because:
- similar numbers stood in one chunk (1.5 kg and 25 kg; 50 m and 200 m);
- the flattened table of annex 2 made the model swap visibility and cloud base.

The report uses this run only for the "before → after" comparison of chunking.
