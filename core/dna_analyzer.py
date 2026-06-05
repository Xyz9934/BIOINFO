from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.fasta_parser import VALID_BASES, normalize_sequence
from core.protein_tools import calculate_molecular_weight, reverse_complement, translate_dna


def create_nucleotide_pie_chart(percentages: Dict[str, float], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    labels = ["A", "T", "G", "C"]
    values = [percentages[label] for label in labels]
    colors = ["#4DA3FF", "#FFD34D", "#3CE58E", "#7E7BFF"]

    fig, ax = plt.subplots(figsize=(4.2, 4.2), facecolor="#0b1220")
    ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=120,
        colors=colors,
        textprops={"color": "white", "fontsize": 10},
    )
    ax.set_facecolor("#0b1220")
    fig.patch.set_facecolor("#0b1220")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def analyze_sequence(raw_sequence: str, chart_output_path: str | None = None) -> Dict[str, Any]:
    sequence, fasta_header = normalize_sequence(raw_sequence)
    counts = {base: sequence.count(base) for base in sorted(VALID_BASES)}
    sequence_length = len(sequence)
    gc_count = counts["G"] + counts["C"]
    gc_content = round((gc_count / sequence_length) * 100, 2)
    percentages = {
        base: round((count / sequence_length) * 100, 2)
        for base, count in counts.items()
    }
    incomplete_codon_bases = sequence_length % 3

    result = {
        "fasta_header": fasta_header,
        "length": sequence_length,
        "gc_content": gc_content,
        "nucleotide_counts": counts,
        "nucleotide_percentages": percentages,
        "molecular_weight": calculate_molecular_weight(counts),
        "reverse_complement": reverse_complement(sequence),
        "rna_transcript": sequence.replace("T", "U"),
        "protein": translate_dna(sequence),
        "complete_codons": sequence_length // 3,
        "incomplete_codon_bases": incomplete_codon_bases,
        "warning": (
            f"Translation ignored the last {incomplete_codon_bases} base(s) because the sequence length is not a multiple of 3."
            if incomplete_codon_bases
            else None
        ),
    }

    if chart_output_path:
        create_nucleotide_pie_chart(percentages, chart_output_path)
        result["pie_chart_path"] = chart_output_path

    return result
