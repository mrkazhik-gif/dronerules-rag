# Assignment 4 - monitoring experiment

| Phase | Requests | Correct | Answers with false value | Alert rate | Block rate | Unchecked | Latency p95, s | Errors | Canary | Store mismatches (last) |
|---|---|---|---|---|---|---|---|---|---|---|
| normal | 44 | 80% | 0 | 0% | 0% | 23% | 5.1 | 0% | 90% | 0 |
| naive | 44 | 80% | 0 | 66% | 0% | 23% | 10.1 | 0% | 90% | 0 |
| recovery | 44 | 80% | 0 | 0% | 0% | 23% | 5.0 | 0% | 90% | 0 |
| stealth | 44 | 80% | 0 | 9% | 0% | 23% | 4.7 | 0% | 90% | 0 |
| compromise | 44 | 50% | 14 | 0% | 0% | 20% | 5.7 | 0% | 40% | 60 |
| compromise_avoid_canary | 44 | 57% | 8 | 0% | 0% | 23% | 5.0 | 0% | 70% | 30 |
| kb_loss | 44 | 75% | 0 | 0% | 0% | 18% | 5.2 | 0% | 90% | 248 |
| latency_sim (SIMULATED) | 44 | 80% | 0 | 0% | 0% | 23% | 7.8 | 0% | 90% | 0 |
| errors_sim (SIMULATED) | 44 | 64% | 0 | 0% | 0% | 14% | 3.9 | 25% | 70% | 0 |
| normal_end | 44 | 80% | 0 | 0% | 0% | 23% | 4.9 | 0% | 90% | 0 |

## Monitor events

| Step | Phase | Event | Indicator | Value | Threshold | Requests since phase start | False-value answers shown in the phase before it |
|---|---|---|---|---|---|---|---|
| 45 | naive | fire | latency_p95 | 13.75 | 9.7 | 1 | 0 |
| 51 | naive | fire | alert_rate | 0.15 | 0.1 | 7 | 0 |
| 81 | naive | clear | latency_p95 | 6.7 | 9.7 | 37 | 0 |
| 83 | naive | fire | latency_p95 | 12.07 | 9.7 | 39 | 0 |
| 103 | recovery | clear | latency_p95 | 8.06 | 9.7 | 15 | 0 |
| 105 | recovery | clear | alert_rate | 0.1 | 0.1 | 17 | 0 |
| 162 | stealth | fire | alert_rate | 0.15 | 0.1 | 30 | 0 |
| 175 | stealth | clear | alert_rate | 0.1 | 0.1 | 43 | 0 |
| 180 | compromise | fire | store_mismatches | 60 | 0 | 4 | 0 |
| 220 | compromise | fire | canary_accuracy | 0.4 | 0.8 | 44 | 14 |
| 308 | kb_loss | clear | canary_accuracy | 0.9 | 0.8 | 44 | 0 |
| 310 | latency_sim | clear | store_mismatches | 0 | 0 | 2 | 0 |
| 360 | errors_sim | fire | error_rate | 0.1 | 0.05 | 8 | 0 |
| 396 | errors_sim | fire | canary_accuracy | 0.7 | 0.8 | 44 | 0 |
| 412 | normal_end | clear | error_rate | 0.05 | 0.05 | 16 | 0 |
| 440 | normal_end | clear | canary_accuracy | 0.9 | 0.8 | 44 | 0 |

Fired during phases without an injected fault: 0
