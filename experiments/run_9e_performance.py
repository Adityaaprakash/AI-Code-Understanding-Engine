from pathlib import Path

from evaluation.benchmark_performance import Benchmarker


def main():
    benchmarker = Benchmarker()
    report = benchmarker.run_all()

    out_dir = Path("results/phase9/9e")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "performance_metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    print(f"9E Performance Metrics written to {json_path}")

    md_path = out_dir / "README.md"

    md = [
        "# Phase 9E — Performance Benchmarking\n",
        "**Under the benchmark environment and workload...**\n",
        f"- OS: {report.environment.os} {report.environment.platform}",
        f"- CPU: {report.environment.cpu} ({report.environment.logical_cpus} logical cores)",
        f"- RAM: {report.environment.ram_bytes / (1024**3):.1f} GB",
        f"- Model: {report.environment.embedding_model}\n",
        "## TABLE A: Full Indexing\n",
        "| Fixture | LOC | Files | Symbols | Chunks | Time (sec) | LOC/sec |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in report.full_indexing:
        stages = ",".join(x.pipeline_stages_measured)
        md.append(
            f"| {x.fixture_name} ({stages}) | {x.loc} | {x.files} | {x.symbols} | {x.chunks} | {x.time_sec:.2f} | {x.loc_per_sec if x.loc_per_sec else 0:.0f} |"
        )

    md.extend(
        [
            "\n## TABLE B: Incremental Indexing\n",
            "| Change Size | Total Files | Invalid Files | Invalid Syms | Full Time (s) | Inc Time (s) | Invalidation Reduction | Speedup |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for x in report.incremental_indexing:
        su = f"{x.speedup:.2f}x" if x.speedup else "N/A"
        wr = (
            f"{x.file_invalidation_reduction_percentage:.1f}%"
            if x.file_invalidation_reduction_percentage is not None
            else "N/A"
        )
        md.append(
            f"| {x.change_size} | {x.total_files_before} | {x.invalidated_files} | {x.invalidated_symbols} | {x.full_time_sec:.2f} | {x.incremental_time_sec:.2f} | {wr} | {su} |"
        )

    md.extend(
        [
            "\n## TABLE C: Embedding\n",
            "| Batch | Warmup | Samples | Mean | P50 | P95 | Throughput (txt/s) |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    if report.embedding:
        for b in report.embedding.batches:
            md.append(
                f"| {b.batch_size} | {b.warmup_count} | {b.measurement_count} | {b.mean_ms:.2f}ms | {b.p50_ms:.2f}ms | {b.p95_ms:.2f}ms | {b.throughput_texts_per_sec:.2f} |"
            )
        md.append(
            f"\nCold start (initialization + first inference): {report.embedding.cold_initialization_plus_first_inference_ms:.2f}ms\n"
        )

    md.extend(
        [
            "\n## TABLE D: Retrieval Systems\n",
            "| System | Queries | Warmup | Mean | P50 | P95 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for sys in report.retrieval:
        md.append(
            f"| {sys.system_id} | {sys.query_count} | {sys.warmup_count} | {sys.mean_ms:.2f}ms | {sys.p50_ms:.2f}ms | {sys.p95_ms:.2f}ms |"
        )

    md.extend(
        [
            "\n## TABLE E: Retrieval Components\n",
            "| Component | Mean | P50 | P95 |",
            "|---|---|---|---|",
        ]
    )
    for comp in report.components:
        md.append(
            f"| {comp.component} | {comp.mean_ms:.2f}ms | {comp.p50_ms:.2f}ms | {comp.p95_ms:.2f}ms |"
        )

    md.extend(
        [
            "\n## TABLE F: Memory Operations\n",
            "| Operation | Baseline | Peak | Delta |",
            "|---|---|---|---|",
        ]
    )
    for mem in report.memory:
        md.append(
            f"| {mem.operation} | {mem.baseline_rss_mb:.1f} MB | {mem.peak_rss_mb:.1f} MB | +{mem.peak_delta_mb:.1f} MB |"
        )

    md.extend(
        [
            "\n## TABLE G: Index Footprint\n",
            "| Component | In-Memory Estimate | Persistent Status |",
            "|---|---|---|",
        ]
    )
    for size in report.index_size:
        if size.in_memory_estimate_bytes is not None:
            b = f"{size.in_memory_estimate_bytes / (1024**2):.2f} MB"
        else:
            b = size.in_memory_estimate_status or "N/A"
        md.append(f"| {size.component} | {b} | {size.persistent_status} |")

    md.extend(
        [
            "\n## TABLE H: Scaling (Synthetic Workloads)\n",
            "| Workload | LOC | Files | Time (s) | LOC/s | Peak RSS |",
            "|---|---|---|---|---|---|",
        ]
    )
    for s in report.scaling:
        stages = ",".join(s.pipeline_stages_measured)
        md.append(
            f"| {s.workload} ({stages}) | {s.loc} | {s.files} | {s.elapsed_seconds:.2f} | {s.throughput_loc_per_sec:.0f} | {s.peak_rss_mb:.1f} MB |"
        )

    md.extend(
        [
            "\n## TABLE I: Failure Accounting\n",
            "| Context | Total | Succeeded | Failed |",
            "|---|---|---|---|",
        ]
    )
    acc = report.failure_accounting
    md.append(
        f"| Indexing (Repos) | {acc.repositories_total} | {acc.repositories_succeeded} | {acc.repositories_failed} |"
    )
    md.append(
        f"| Retrieval (Queries)| {acc.queries_total} | {acc.queries_succeeded} | {acc.queries_failed} |"
    )

    md.extend(
        [
            "\n## TABLE J: Reranker Component\n",
            "| Candidates | Queries | Mean | P50 | P95 |",
            "|---|---|---|---|---|",
        ]
    )
    for rr in report.reranker:
        md.append(
            f"| {rr.candidate_count} | {rr.query_count} | {rr.mean_ms:.2f}ms | {rr.p50_ms:.2f}ms | {rr.p95_ms:.2f}ms |"
        )

    md.append("\n## LIMITATIONS\n")
    for lam in report.limitations:
        md.append(f"- {lam}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"9E Markdown Report written to {md_path}")


if __name__ == "__main__":
    main()
