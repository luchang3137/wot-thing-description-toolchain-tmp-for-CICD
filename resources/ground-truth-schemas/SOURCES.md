# Ground-Truth Schema Sources

Copied from [w3c/wot-thing-description](https://github.com/w3c/wot-thing-description),
file `validation/td-json-schema-validation.json`.

| File | Source | Commit SHA | Date |
|------|--------|------------|------|
| `td11-json-schema-validation.json` | Tag `REC1.1` | `7c0b968f403ecdb9594bd882cafbacf544c41fc0` | 2026-07-13 |
| `td20-json-schema-validation.json` | Branch `main` | `18b7ca0e2aa0c6b2247a8e23bdb3ef3f932f0fa1` | 2026-07-13 |

## Re-vendoring

```bash
# TD 1.1 (REC1.1 tag)
curl -sL https://raw.githubusercontent.com/w3c/wot-thing-description/REC1.1/validation/td-json-schema-validation.json \
  -o resources/ground-truth-schemas/td11-json-schema-validation.json

# TD 2.0 / wot-next (main branch, replace <SHA> with the commit to pin)
curl -sL https://raw.githubusercontent.com/w3c/wot-thing-description/<SHA>/validation/td-json-schema-validation.json \
  -o resources/ground-truth-schemas/td20-json-schema-validation.json
```

## Legacy files

`td-json-schema-validation.json` and `tm-json-schema-validation.json` are older hand-modified copies
that do not match any upstream commit. They are kept for reference; the tests use the `td11-` and
`td20-` prefixed files above.
