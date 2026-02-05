# Offer Status Update - Python

Bulk update offer statuses (accept/decline) from a CSV file.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create `config.json` with your credentials:
   ```json
   {
     "client_id": "your_client_id",
     "client_secret": "your_client_secret",
     "environment": "dev"
   }
   ```

3. Create a CSV file with offers to update (see format below)

4. Run:
   ```bash
   python offer_status_client.py --csv your_file.csv
   ```

## CSV Format

| Column   | Description           |
|----------|-----------------------|
| offer_id | UUID of the offer     |
| action   | `accept` or `decline` |

Example:
```csv
offer_id,action
38ef384c-739d-4cf6-a319-c84d4ac62f8b,accept
833c3c9d-ba46-4539-9b69-9281b98c2f61,decline
```

## Offer Statuses

| Status       | Description                                             |
|--------------|---------------------------------------------------------|
| **Offered**  | Initial state - offer has been made to the family       |
| **Accepted** | Family accepted the offer                               |
| **Declined** | Family declined the offer                               |
| **Revoked**  | Admin revoked the offer (not available via this script) |

You can use this script to change offers to `Accepted` or `Declined`. Offers can be transitioned between these states (e.g., Accepted → Declined).

> [!NOTE]
> For large batches (1000+ offers), consider splitting your CSV into smaller files to avoid timeout issues.

## Options

```bash
# Dry run - see what would happen without making changes
python offer_status_client.py --dry-run

# Use a specific CSV file
python offer_status_client.py --csv /path/to/offers.csv
```

## Finding Offer IDs

You can find offer IDs in the Avela Admin UI under Forms → Offers tab, or via database query:

```sql
SELECT offer.id, offer.status, school.name
FROM offer
JOIN school ON school.id = offer.school_id
WHERE offer.status = 'Offered'
  AND offer.deleted_at IS NULL;
```
