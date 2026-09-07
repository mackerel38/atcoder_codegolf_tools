#!/usr/bin/env python3
"""Generate deterministic regression cases for ABC468 A-D."""
from __future__ import annotations

from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent


def write(task: str, name: str, input_text: str, answer: int) -> None:
    directory = ROOT / task / "cases"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.in").write_text(input_text)
    (directory / f"{name}.out").write_text(f"{answer}\n")


def solve_a(values: list[int]) -> int:
    return sum(x < y > z for x, y, z in zip(values, values[1:], values[2:]))


def solve_b(m: int, d: int, corridor: str) -> int:
    return sum(
        all(corridor[j] != "G" for j in range(max(0, i - d), min(m, i + d + 1)))
        for i in range(m)
    )


def rank(permutation: tuple[int, ...]) -> int:
    values = list(permutation)
    result = 0
    for i, value in enumerate(values):
        result += sum(other < value for other in values[i + 1 :]) * factorial(
            len(values) - i - 1
        )
    return result


def factorial(n: int) -> int:
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result


def solve_d(s: str) -> int:
    result = 0
    for center in range(2 * len(s) - 1):
        left, right = center // 2, (center + 1) // 2
        mismatches = 0
        while left >= 0 and right < len(s):
            mismatches += s[left] != s[right]
            if mismatches == 2:
                break
            result += 1
            left -= 1
            right += 1
    return result


def main() -> None:
    rng = random.Random(468)

    samples_a = [
        [3, 1, 4, 1, 5, 2],
        [1, 1, 1, 2, 1],
        [7, 3, 9, 8, 10, 3, 1, 5, 5, 4],
    ]
    for i, values in enumerate(samples_a, 1):
        write("a", f"sample{i}", f"{len(values)}\n{' '.join(map(str, values))}\n", solve_a(values))
    for i in range(40):
        values = [rng.randrange(1, 101) for _ in range(rng.randrange(3, 101))]
        write("a", f"random{i:02}", f"{len(values)}\n{' '.join(map(str, values))}\n", solve_a(values))

    samples_b = [(7, 1, ".G...GG"), (6, 5, "......"), (21, 2, "....G...GG.....G.....")]
    for i, (m, d, corridor) in enumerate(samples_b, 1):
        write("b", f"sample{i}", f"{m} {d}\n{corridor}\n", solve_b(m, d, corridor))
    for i in range(40):
        m = rng.randrange(1, 101)
        d = rng.randrange(1, m + 1)
        corridor = "".join(rng.choice(".G") for _ in range(m))
        write("b", f"random{i:02}", f"{m} {d}\n{corridor}\n", solve_b(m, d, corridor))

    samples_c = [
        ((1, 3, 2), (3, 1, 2)),
        ((5, 4, 2, 1, 3), (5, 1, 2, 3, 4)),
        ((3, 6, 5, 2, 7, 1, 4), (4, 1, 5, 7, 2, 3, 6)),
    ]
    for i, (p, q) in enumerate(samples_c, 1):
        answer = max(0, rank(q) - rank(p) - 1)
        write("c", f"sample{i}", f"{len(p)}\n{' '.join(map(str, p))}\n{' '.join(map(str, q))}\n", answer)
    for i in range(40):
        n = rng.randrange(2, 9)
        p = tuple(rng.sample(range(1, n + 1), n))
        q = tuple(rng.sample(range(1, n + 1), n))
        answer = max(0, rank(q) - rank(p) - 1)
        write("c", f"random{i:02}", f"{n}\n{' '.join(map(str, p))}\n{' '.join(map(str, q))}\n", answer)

    samples_d = ["ababa", "atcoder", "abccbacbacb"]
    for i, s in enumerate(samples_d, 1):
        write("d", f"sample{i}", f"{s}\n", solve_d(s))
    for i in range(40):
        s = "".join(rng.choice("abcd") for _ in range(rng.randrange(1, 80)))
        write("d", f"random{i:02}", f"{s}\n", solve_d(s))


if __name__ == "__main__":
    main()
