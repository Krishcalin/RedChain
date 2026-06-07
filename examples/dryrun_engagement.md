# Example: dry-run engagement

This walkthrough exercises RedChain without an API key, using the bundled fixtures.

```bash
pip install -e ".[dev]"

redchain engage \
  --preset webapp \
  --target https://app.example.com \
  --out ./engagements/dryrun-001 \
  --dry-run
```

After the run, inspect the artifacts:

```bash
ls engagements/dryrun-001/
#  manifest.yaml  state.sqlite  artifacts/  transcripts/

cat engagements/dryrun-001/artifacts/scope_brief.md
cat engagements/dryrun-001/artifacts/recon_dossier.md
cat engagements/dryrun-001/artifacts/executive_report.md

redchain status ./engagements/dryrun-001
```

Trigger a gate failure by editing `scope_brief.md` to remove the `## In Scope` section, then:

```bash
redchain resume ./engagements/dryrun-001
# Gate fails — fix the section and re-run resume to advance.
```
