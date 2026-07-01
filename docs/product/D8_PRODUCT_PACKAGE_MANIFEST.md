# D8 Product Package Manifest

The Phase 12 package command creates:

```text
runtime/total_field/product_demo/D8_PRODUCT_DEMO_PACKAGE_<timestamp>/
```

Each package includes:

- D8_PRODUCT_DEMO_PACKAGE_MANIFEST.json
- D8_PRODUCT_DEMO_PACKAGE_MANIFEST.tsv
- D8_PRODUCT_DEMO_SHA256SUMS.txt
- D8_PRODUCT_DEMO_README_COPY.md
- D8_PRODUCT_DEMO_QUICKSTART_COPY.md
- D8_PRODUCT_DEMO_SCRIPT_COPY.md

The manifest records product demo tools, product documents, latest phase reports, latest seals, and latest backup paths. Backup dump files are recorded as paths only. `.env` and `.env.d8.local` are not hashed or copied; the package may record existence and permission-check status without reading content.

Primary tools:

- tools/d8_product_demo_launcher.py
- tools/d8_product_demo_launcher.sh
- tools/d8_local_dashboard.py
- tools/d8_voice_operator.py
- tools/d8_odoo_pos_safe_bridge.py
- tools/d8_total_field_console.sh
- tools/d8_codex_mandatory_workflow.sh

Primary merchant invention integration documents:

- docs/product/XIAOJ_MERCHANT_SYSTEM_INVENTION_CAPABILITY_INTEGRATION.md
- packets/product_av_ordering_ai/merchant_invention_capability_map.json
