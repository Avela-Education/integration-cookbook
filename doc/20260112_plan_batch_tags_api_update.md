# Plan: Update Form-School Tags Import to Use Batch API

**Date:** January 12, 2026
**Status:** Draft
**Depends On:** Customer API PR #81 (feat/ed/batch-tag-upload)

---

## Goal

Update `form_school_tags_import.py` to use the new batch endpoints, reducing import time from ~6 hours to ~3.5 minutes for large datasets (6,000+ tags).

## Background

The current script makes individual API calls for each row:
```
POST /tags/forms/{form_id}/schools/{school_id}
```

This hits the rate limit (100 requests per 5 minutes) and requires 3.3s delays between requests.

The new batch endpoints accept up to 100 operations per request:
```
POST /tags/schools/batch
DELETE /tags/schools/batch
```

## New Batch API

### Request
```json
{
  "operations": [
    { "form_id": "uuid-1", "school_id": "uuid-a", "tag_id": "uuid-x" },
    { "form_id": "uuid-2", "school_id": "uuid-b", "tag_id": "uuid-x" }
  ]
}
```

### Response (207 Multi-Status)
Results are grouped by `tag_id`:
```json
{
  "request_id": "optional-correlation-id",
  "responses": [
    {
      "status": "201",
      "tag_id": "uuid-x",
      "affected_rows": 2,
      "requested": 2,
      "fully_applied": true
    },
    {
      "status": "404",
      "tag_id": "uuid-y",
      "error": "Tag not found",
      "requested": 1
    }
  ]
}
```

### Key Behaviors
- **Max 100 operations per request**
- **Results grouped by tag_id** (not per-item)
- **`fully_applied: false`** means some operations were skipped (duplicates or invalid form-school pairs)
- **One tag group failing doesn't affect others**

---

## Implementation Plan

### Phase 1: Add Batch Functions

**File:** `form_school_tags_import.py`

1. Add `chunk_operations()` helper:
   ```python
   def chunk_operations(
       records: list[tuple[str, str, str, int]],
       tag_cache: dict[str, str],
       chunk_size: int = 100
   ) -> list[list[dict]]:
       """
       Convert CSV records to batch operation chunks.

       Returns list of chunks, each chunk is a list of:
       {"form_id": str, "school_id": str, "tag_id": str, "csv_line": int}
       """
   ```

2. Add `add_tags_batch()` function:
   ```python
   def add_tags_batch(
       client: AvelaClient,
       operations: list[dict]
   ) -> tuple[int, int, list[tuple[int, str]]]:
       """
       Add tags via batch endpoint.

       Args:
           client: Authenticated AvelaClient
           operations: List of {"form_id", "school_id", "tag_id", "csv_line"}

       Returns:
           Tuple of (affected_count, skipped_count, errors_list)
       """
       response = client.post('/tags/schools/batch', json={
           'operations': [
               {'form_id': op['form_id'], 'school_id': op['school_id'], 'tag_id': op['tag_id']}
               for op in operations
           ]
       })
       # Handle 207 Multi-Status response
       # Aggregate results across tag groups
   ```

3. Add `delete_tags_batch()` with same pattern for DELETE.

### Phase 2: Update Main Processing

1. Modify `process_tags()` to use batch mode by default:
   ```python
   def process_tags(..., batch_mode: bool = True):
       if batch_mode:
           return process_tags_batch(...)
       else:
           return process_tags_sequential(...)  # Existing logic
   ```

2. Add `--sequential` flag to fall back to single-item calls (for debugging).

3. Update progress reporting:
   - Current: "500/1500 (33%)..."
   - New: "Batch 5/15 (500 operations)..."

### Phase 3: Handle Partial Success

The batch endpoint returns `fully_applied: false` when some operations in a tag group are skipped. We need to:

1. Track which tag groups had partial success
2. Report partial success in summary:
   ```
   Results:
     Inserted: 1,180
     Already existed: 300
     Partial success: 2 tag groups (some ops skipped)
     Failed tag groups: 1
   ```

3. Optionally add `--strict` flag that treats partial success as error.

### Phase 4: Update Documentation

1. Update `README.md` with:
   - New batch mode (default)
   - `--sequential` flag for fallback
   - Updated performance expectations

2. Add note about API version requirement (Customer API v2.3.0+)

---

## Files to Modify

| File | Changes |
|------|---------|
| `form_school_tags_import.py` | Add batch functions, update process_tags() |
| `README.md` | Document batch mode, new flags, performance |

## New CLI Flags

| Flag | Description |
|------|-------------|
| `--sequential` | Use single-item API calls (old behavior) |
| `--strict` | Treat partial success as error |
| `--batch-size N` | Operations per batch (default: 100, max: 100) |

---

## Testing Checklist

- [ ] Batch mode with small CSV (< 100 rows) - single batch
- [ ] Batch mode with large CSV (> 100 rows) - multiple batches
- [ ] Mixed tag IDs in same batch - verify grouping
- [ ] Partial success handling (some duplicates)
- [ ] 404 error for invalid tag - verify other groups succeed
- [ ] `--sequential` fallback works
- [ ] `--dry-run` still works
- [ ] `--delete` mode uses batch DELETE endpoint
- [ ] Progress reporting shows batch progress

---

## Performance Comparison

| Scenario | Current (Sequential) | New (Batch) |
|----------|---------------------|-------------|
| 100 tags | 5.5 min | 1 request (~1s) |
| 1,000 tags | 55 min | 10 requests (~10s) |
| 6,438 tags | 5.9 hours | 65 requests (~1 min) |

---

## Rollout

1. **Prerequisite:** Customer API PR #81 merged and deployed to target environment
2. Create feature branch in integration-cookbook
3. Implement changes
4. Test against QA environment
5. Update documentation
6. Merge to main

---

## Open Questions

1. Should we retry failed tag groups automatically?
2. Should `--strict` be the default for production use?
3. Do we need a `--request-id` flag for debugging correlation?
