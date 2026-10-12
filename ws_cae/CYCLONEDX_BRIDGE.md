# WS-CAE CycloneDX Bridge

WS-CAE can export `WS-CAE-CRYPTO-SYSTEM-PATCH-1` into CycloneDX 1.7 JSON.

Purpose: make cryptocurrency authority/dependency state consumable by existing CBOM/xBOM security inventory tooling without changing the upstream CycloneDX standard.

The bridge preserves WS-CAE-specific semantics as namespaced properties:

- `ws-cae:role`
- `ws-cae:readiness-state`
- `ws-cae:critical`
- `ws-cae:evidence-documented`
- `ws-cae:system-state`
- `ws-cae:weakest-readiness-state`
- `ws-cae:valid`

The evaluated cryptocurrency position is represented as the BOM metadata component. Declared system dependencies are emitted as standard CycloneDX components and linked through the CycloneDX dependency graph.

## Export

```bash
python -m ws_cae.cyclonedx_cli path/to/crypto-system.patch.json --pretty > crypto-system.cdx.json
```

## Reusable action

```yaml
- uses: actions/checkout@v4
- uses: Bdavis1390/Sara_pro/.github/actions/ws-cae-cyclonedx@<pinned-commit>
  with:
    patch: path/to/crypto-system.patch.json
    output: crypto-system.cdx.json
```

## Validation

The WS-CAE standalone workflow generates a CycloneDX 1.7 BOM and validates it with the upstream `cyclonedx/cyclonedx-cli` validator using `--input-version v1_7 --fail-on-errors`.

## Scope boundary

This is an interoperability mapping, not a new CycloneDX specification and not an endorsement by OWASP, Ecma International, CycloneDX, NIST, or any other standards body. WS-CAE does not replace CBOM; it provides digital-asset authority/dependency semantics that can travel through the existing BOM ecosystem.
