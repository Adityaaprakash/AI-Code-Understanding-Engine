# Phase 9E — Performance Benchmarking

**Under the benchmark environment and workload...**

- OS: Windows Windows-11-10.0.26200-SP0
- CPU: AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD (12 logical cores)
- RAM: 7.3 GB
- Model: all-MiniLM-L6-v2

## TABLE A: Full Indexing

| Fixture | LOC | Files | Symbols | Chunks | Time (sec) | LOC/sec |
|---|---|---|---|---|---|---|
| repo-py-ecommerce-001 (lexical_indexing,embedding_inference,vector_indexing) | 198 | 13 | 22 | 22 | 0.02 | 8131 |
| repo-java-banking-001 (lexical_indexing,embedding_inference,vector_indexing) | 81 | 9 | 9 | 9 | 0.01 | 9901 |
| repo-ts-gateway-001 (lexical_indexing,embedding_inference,vector_indexing) | 90 | 10 | 10 | 10 | 0.01 | 12324 |

## TABLE B: Incremental Indexing

| Change Size | Total Files | Invalid Files | Invalid Syms | Full Time (s) | Inc Time (s) | Invalidation Reduction | Speedup |
|---|---|---|---|---|---|---|---|
| 0 files | 100 | 0 | 0 | 0.50 | 0.18 | 100.0% | 2.71x |
| 1 files | 100 | 1 | 1 | 0.50 | 0.39 | 99.0% | 1.27x |
| 10 files | 100 | 10 | 10 | 0.50 | 1.63 | 90.0% | 0.31x |

## TABLE C: Embedding

| Batch | Warmup | Samples | Mean | P50 | P95 | Throughput (txt/s) |
|---|---|---|---|---|---|---|
| 1 | 3 | 10 | 17.51ms | 17.14ms | 19.71ms | 57.10 |
| 8 | 3 | 10 | 39.88ms | 40.77ms | 42.67ms | 200.58 |
| 16 | 3 | 10 | 69.69ms | 67.67ms | 76.75ms | 229.60 |
| 32 | 3 | 10 | 116.13ms | 115.89ms | 123.56ms | 275.55 |
| 64 | 3 | 10 | 257.74ms | 231.43ms | 390.96ms | 248.31 |

Cold start (initialization + first inference): 27451.98ms


## TABLE D: Retrieval Systems

| System | Queries | Warmup | Mean | P50 | P95 |
|---|---|---|---|---|---|
| System A | 48 | 5 | 0.57ms | 0.55ms | 0.72ms |
| System B | 48 | 5 | 1.13ms | 1.16ms | 1.45ms |
| System C | 48 | 5 | 1.38ms | 1.37ms | 1.88ms |
| System D | 48 | 5 | 1.70ms | 1.74ms | 2.32ms |

## TABLE E: Retrieval Components

| Component | Mean | P50 | P95 |
|---|---|---|---|
| BM25 | 0.43ms | 0.41ms | 0.71ms |
| Vector | 0.56ms | 0.53ms | 0.75ms |
| Graph | 0.28ms | 0.26ms | 0.50ms |
| Fusion | 0.17ms | 0.18ms | 0.26ms |

## TABLE F: Memory Operations

| Operation | Baseline | Peak | Delta |
|---|---|---|---|
| Cold Start Embedding Provider | 82.9 MB | 494.3 MB | +411.4 MB |
| Post-Indexing Settled Memory | 82.9 MB | 504.0 MB | +421.1 MB |

## TABLE G: Index Footprint

| Component | In-Memory Estimate | Persistent Status |
|---|---|---|
| BM25 | NOT_MEASURED | NOT_PERSISTED |
| Vector | NOT_MEASURED | NOT_PERSISTED |
| Graph | NOT_MEASURED | NOT_PERSISTED |

## TABLE H: Scaling (Synthetic Workloads)

| Workload | LOC | Files | Time (s) | LOC/s | Peak RSS |
|---|---|---|---|---|---|
| synthetic_small (parsing,lexical_indexing) | 1000 | 10 | 0.01 | 85690 | 0.0 MB |
| synthetic_medium (parsing,lexical_indexing) | 10000 | 50 | 0.12 | 85764 | 504.0 MB |

## TABLE I: Failure Accounting

| Context | Total | Succeeded | Failed |
|---|---|---|---|
| Indexing (Repos) | 3 | 3 | 0 |
| Retrieval (Queries)| 48 | 48 | 0 |

## TABLE J: Reranker Component

| Candidates | Queries | Mean | P50 | P95 |
|---|---|---|---|---|
| 20 | 48 | 0.36ms | 0.36ms | 0.57ms |

## LIMITATIONS
