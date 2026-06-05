from __future__ import annotations

from typing import Any, Dict, List


def needleman_wunsch(seq1: str, seq2: str, match_score: int = 1, mismatch_score: int = -1, gap_penalty: int = -1) -> Dict[str, Any]:
    rows = len(seq1) + 1
    cols = len(seq2) + 1
    score = [[0 for _ in range(cols)] for _ in range(rows)]
    trace = [["" for _ in range(cols)] for _ in range(rows)]

    for i in range(1, rows):
        score[i][0] = i * gap_penalty
        trace[i][0] = "up"
    for j in range(1, cols):
        score[0][j] = j * gap_penalty
        trace[0][j] = "left"

    for i in range(1, rows):
        for j in range(1, cols):
            diag = score[i - 1][j - 1] + (match_score if seq1[i - 1] == seq2[j - 1] else mismatch_score)
            up = score[i - 1][j] + gap_penalty
            left = score[i][j - 1] + gap_penalty
            best = max(diag, up, left)
            score[i][j] = best
            if best == diag:
                trace[i][j] = "diag"
            elif best == up:
                trace[i][j] = "up"
            else:
                trace[i][j] = "left"

    aligned1: List[str] = []
    aligned2: List[str] = []
    markers: List[str] = []
    i = len(seq1)
    j = len(seq2)

    while i > 0 or j > 0:
        direction = trace[i][j] if i >= 0 and j >= 0 else ""
        if i > 0 and j > 0 and direction == "diag":
            a = seq1[i - 1]
            b = seq2[j - 1]
            aligned1.append(a)
            aligned2.append(b)
            markers.append("|" if a == b else ".")
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or direction == "up"):
            aligned1.append(seq1[i - 1])
            aligned2.append("-")
            markers.append(" ")
            i -= 1
        else:
            aligned1.append("-")
            aligned2.append(seq2[j - 1])
            markers.append(" ")
            j -= 1

    aligned_seq1 = "".join(reversed(aligned1))
    aligned_seq2 = "".join(reversed(aligned2))
    marker_line = "".join(reversed(markers))
    identity_matches = sum(1 for a, b in zip(aligned_seq1, aligned_seq2) if a == b and a != "-")
    ungapped_positions = sum(1 for a, b in zip(aligned_seq1, aligned_seq2) if a != "-" and b != "-")
    identity = round((identity_matches / ungapped_positions) * 100, 2) if ungapped_positions else 0.0

    return {
        "aligned_seq1": aligned_seq1,
        "aligned_seq2": aligned_seq2,
        "marker_line": marker_line,
        "score": score[-1][-1],
        "identity_percent": identity,
    }
