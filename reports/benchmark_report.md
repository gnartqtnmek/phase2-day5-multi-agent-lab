# Benchmark Report

## Goal
So sanh single-agent baseline va multi-agent workflow.

## Test Queries
- Research GraphRAG state-of-the-art and summarize practical tradeoffs.
- Compare vector databases for enterprise RAG deployment in 2026.
- What are robust evaluation strategies for multi-agent research assistants?

## Metrics
| Run | Latency | Cost | Quality | Citation coverage | Failure rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| baseline:Research GraphRAG state- | 12.46s | 0.0004 | 4.0 | 0.00% | 0% | iterations=0 | routes=n/a |
| multi-agent:Research GraphRAG state- | 31.48s | 0.0016 | 7.8 | 80.00% | 0% | iterations=4 | routes=researcher,analyst,writer,done |
| baseline:Compare vector databases | 12.75s | 0.0005 | 4.0 | 0.00% | 0% | iterations=0 | routes=n/a |
| multi-agent:Compare vector databases | 26.67s | 0.0017 | 8.0 | 100.00% | 0% | iterations=4 | routes=researcher,analyst,writer,done |
| baseline:What are robust evaluati | 7.36s | 0.0003 | 4.0 | 0.00% | 0% | iterations=0 | routes=n/a |
| multi-agent:What are robust evaluati | 29.05s | 0.0016 | 7.8 | 80.00% | 0% | iterations=4 | routes=researcher,analyst,writer,done |

## Trace Summary
- Research GraphRAG state-of-the-art and summarize... | baseline routes=['single'] | multi routes=['researcher', 'analyst', 'writer', 'done']
- Compare vector databases for enterprise RAG depl... | baseline routes=['single'] | multi routes=['researcher', 'analyst', 'writer', 'done']
- What are robust evaluation strategies for multi-... | baseline routes=['single'] | multi routes=['researcher', 'analyst', 'writer', 'done']

## Failure Modes
- Missing API keys or provider package -> fallback to deterministic mock responses.
- Search provider timeout/network errors -> fallback to mock search sources.
- Incomplete intermediate notes -> downstream agents run with conservative fallback prompts.
- Excessive errors or too many iterations -> supervisor routes to `done` to avoid infinite loop.

## Conclusion
Multi-agent phu hop khi bai toan can tach buoc research/analysis/writing de de kiem soat chat luong, nhung single-agent phu hop hon cho cau hoi ngan hoac khi can latency thap.
