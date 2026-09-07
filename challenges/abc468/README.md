# ABC468 code-golf workspace

Target byte counts:

| Task | Target | Candidate language |
| --- | ---: | --- |
| A | 21 | A language |
| B | 37 | Uiua 0.16.2 |
| C | 59 | Uiua 0.16.2 |
| D | 87 | cLay |

Regenerate the deterministic sample and randomized regression cases with:

```sh
python3 challenges/abc468/generate_cases.py
```

Count candidate bytes and run local cases with:

```sh
./bootstrap.sh bytes challenges/abc468/*/main.*
./bootstrap.sh test uiua challenges/abc468/b/main.ua challenges/abc468/b/cases
```

Use `./bootstrap.sh remote ...` for cLay and the other remote-only runtimes.
