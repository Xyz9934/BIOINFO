from __future__ import annotations

from typing import Dict, List, Tuple


VALID_BASES = {"A", "T", "G", "C"}


def parse_fasta(raw_sequence: str) -> Tuple[str, str | None]:
    cleaned = raw_sequence.strip()
    if not cleaned:
        raise ValueError("Sequence cannot be empty.")

    if cleaned.startswith(">"):
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        header = lines[0][1:].strip()
        if not header:
            raise ValueError("FASTA header is present but empty.")
        sequence = "".join(lines[1:])
        if not sequence:
            raise ValueError("FASTA sequence is missing below the header.")
        return sequence, header

    return cleaned, None


def normalize_sequence(raw_sequence: str) -> Tuple[str, str | None]:
    sequence_text, fasta_header = parse_fasta(raw_sequence)
    sequence = sequence_text.upper().replace(" ", "").replace("\t", "").replace("\r", "").replace("\n", "")
    if not sequence:
        raise ValueError("Sequence cannot be empty after cleanup.")

    invalid_bases = sorted({base for base in sequence if base not in VALID_BASES})
    if invalid_bases:
        raise ValueError(
            "Invalid DNA sequence. Only A, T, G, and C are allowed. "
            f"Unsupported characters found: {', '.join(invalid_bases)}"
        )
    return sequence, fasta_header


def parse_multi_fasta(raw_text: str) -> List[Dict[str, str]]:
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("FASTA content cannot be empty.")

    if not cleaned.startswith(">"):
        sequence, header = normalize_sequence(cleaned)
        return [{"header": header or "sequence_1", "sequence": sequence}]

    records: List[Dict[str, str]] = []
    chunks = [chunk for chunk in cleaned.split(">") if chunk.strip()]
    for index, chunk in enumerate(chunks, start=1):
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        header = lines[0] or f"sequence_{index}"
        sequence_text = "".join(lines[1:])
        sequence, _ = normalize_sequence(sequence_text)
        records.append({"header": header, "sequence": sequence})

    if not records:
        raise ValueError("No FASTA records found.")

    return records
