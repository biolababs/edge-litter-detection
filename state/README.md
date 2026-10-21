# Runtime state

Native runs store persistent operational data in:

```text
state/litter-edge.db
```

SQLite may also create `litter-edge.db-wal` and `litter-edge.db-shm` while the
application is running. These runtime files are ignored by Git.

The database contains observed counts, run metadata, vehicle/route identifiers,
human-review records, explicit collection confirmations, and integration
outbox events. Protect and retain it according to the operating organization's
privacy and records policy.

Query it through:

```bash
python query_counts.py summary
./startup.sh --counts-api
```
