from __future__ import annotations

from typing import Dict


CODON_TABLE: Dict[str, str] = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "TAT": "Y",
    "TAC": "Y",
    "TAA": "*",
    "TAG": "*",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "TGT": "C",
    "TGC": "C",
    "TGA": "*",
    "TGG": "W",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}

COMPLEMENT = str.maketrans({"A": "T", "T": "A", "G": "C", "C": "G"})
NUCLEOTIDE_WEIGHTS = {
    "A": 313.21,
    "T": 304.20,
    "G": 329.21,
    "C": 289.18,
}


def reverse_complement(sequence: str) -> str:
    return sequence.translate(COMPLEMENT)[::-1]


def translate_dna(sequence: str) -> str:
    protein = []
    for index in range(0, len(sequence) - 2, 3):
        codon = sequence[index : index + 3]
        protein.append(CODON_TABLE.get(codon, "?"))
    return "".join(protein)


def calculate_molecular_weight(counts: Dict[str, int]) -> float:
    return round(sum(NUCLEOTIDE_WEIGHTS[base] * count for base, count in counts.items()), 2)
