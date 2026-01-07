# Customer API - Update Form Answers from CSV

This example demonstrates how to update form answers in bulk by reading updates from a CSV file using the Avela Customer API.

## Overview

This integration script shows you how to:
1. Authenticate with the Avela API using OAuth2 client credentials
2. Read form update data from a CSV file
3. Update form answers by question key using the Customer API
4. Handle different question types (FreeText, Email, PhoneNumber, etc.)

## Why Use the Customer API?

This example uses the **Customer API** (`/api/rest/v2/forms/{id}/questions`) instead of the Forms Service API because it:
- **Simpler workflow** - Update answers directly by question key without fetching templates
- **No schema version issues** - Handles form template versions internally
- **Batch updates** - Update multiple questions in a single API call
- **Same authentication** - Uses the same OAuth2 credentials as other Avela APIs

## Prerequisites

Before running this example, you'll need:

- **Python 3.10 or higher** installed on your system
- **API Credentials** from Avela (client_id and client_secret)
- **Form IDs and Question Keys** you want to update

## Installation

### 1. Navigate to this example

```bash
cd integration-cookbook/api/forms-update-csv-python
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Create your configuration file

Copy the example configuration file and fill in your credentials:

```bash
cp config.example.json config.json
```

### 2. Edit `config.json` with your credentials

```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "environment": "uat"
}
```

**Environment options:**
- `dev` - Development environment
- `qa` - QA environment
- `uat` - UAT environment
- `prod` - Production environment

### 3. Prepare your CSV file

Create or edit `sample_updates.csv` with your form updates:

```csv
form_id,question_key,question_type,answer_value
e4c2f10d-b94a-49eb-b6b2-a129b0840f90,internal1,FreeText,Test Answer Value
e4c2f10d-b94a-49eb-b6b2-a129b0840f90,student_email,Email,john@example.com
f5d3e20e-c05b-50fc-c7c3-b230c0951fa1,grade_level,Number,9
```

**CSV Format:**
- `form_id` - The UUID of the form instance to update
- `question_key` - The key of the question (e.g., "internal1", "student_name")
- `question_type` - The type of question (FreeText, Email, PhoneNumber, Number, Date, SingleSelect)
- `answer_value` - The new answer value to set

**Note:** The `question_type` column is optional and defaults to "FreeText" if not provided.

## Usage

### Run the script

```bash
python form_update_client.py
```

### Expected Output

```
================================================================================
AVELA CUSTOMER API - UPDATE FORM ANSWERS FROM CSV
================================================================================

Authenticating with Avela API (uat)...
✓ Authentication successful! Token expires in 86400 seconds.

✓ Read 3 updates from CSV file

Processing updates for 2 form(s)...

Form: e4c2f10d-b94a-49eb-b6b2-a129b0840f90
  2 update(s) to process
  • internal1 (FreeText) = "Test Answer Value"
  • student_email (Email) = "john@example.com"
  Submitting 2 question(s) to API... ✓

Form: f5d3e20e-c05b-50fc-c7c3-b230c0951fa1
  1 update(s) to process
  • grade_level (Number) = "9"
  Submitting 1 question(s) to API... ✓

================================================================================
RESULTS
================================================================================
✓ Successful updates: 3
✗ Failed updates: 0
Total: 3
================================================================================

✓ Integration completed successfully!
```

## What This Example Does

1. **Loads Configuration** - Reads your API credentials from `config.json`

2. **Authenticates** - Uses OAuth2 client credentials flow to get an access token for the Customer API

3. **Reads CSV** - Parses the `sample_updates.csv` file and validates the format

4. **Groups by Form** - Organizes updates by form_id to batch updates efficiently

5. **Builds Answer Objects** - Converts answer values to the correct format based on question type

6. **Updates Answers** - Sends POST requests to `/api/rest/v2/forms/{id}/questions` with batched updates

7. **Reports Results** - Displays success/failure counts for all updates

## API Endpoint Used

This example uses the Customer API endpoint:

### Update Form Questions
```
POST /api/rest/v2/forms/{formId}/questions
```

**Request body:**
```json
{
  "questions": [
    {
      "key": "internal1",
      "type": "FreeText",
      "answer": {
        "free_text": {
          "value": "Test Answer Value"
        }
      }
    },
    {
      "key": "student_email",
      "type": "Email",
      "answer": {
        "email": {
          "value": "john@example.com"
        }
      }
    }
  ]
}
```

## Question Types and Answer Formats

Different question types require different answer structures:

| Question Type | Answer Format | CSV Example |
|--------------|---------------|-------------|
| FreeText | `{"free_text": {"value": "..."}}` | `key,FreeText,John Doe` |
| Email | `{"email": {"value": "..."}}` | `email,Email,john@example.com` |
| PhoneNumber | `{"phone_number": {"value": "..."}}` | `phone,PhoneNumber,555-0123` |
| Number | `{"number": {"value": 42}}` | `age,Number,42` |
| Date | `{"date": {"value": "2024-03-15"}}` | `dob,Date,2024-03-15` |
| SingleSelect | `{"single_select": {"value": "uuid"}}` | `choice,SingleSelect,option-uuid` |

**Note:** For SingleSelect, the answer_value should be the UUID of the selected option, not the label.

## Common Issues

### 401 Unauthorized Error

**Problem:** You receive a 401 error when trying to authenticate or update.

**Solution:**
- Verify your `client_id` and `client_secret` are correct
- Ensure your credentials have access to the specified environment
- Check that the environment name is correct (dev, qa, uat, prod)

### 404 Not Found - Form Not Found

**Problem:** Error indicates the form doesn't exist.

**Solution:**
- Verify the form_id UUID is correct
- Ensure the form exists in the specified environment
- Check that your API credentials have access to this form

### Invalid Question Key

**Problem:** API returns an error about invalid question key.

**Solution:**
- Verify the question_key matches exactly (case-sensitive)
- Ensure the question exists in the form template
- Check for typos in the CSV file

### Answer Validation Errors

**Problem:** API rejects the answer value.

**Solution:**
- Ensure the question_type matches the actual question type in the form
- Check that the answer value matches the expected format (e.g., valid email, valid date)
- For SingleSelect, use the option UUID, not the label
- For Number types, ensure the value is numeric

## Security Best Practices

- **Never commit `config.json`** - This file is in `.gitignore` for a reason
- **Keep credentials secure** - Store in environment variables or secure vaults in production
- **Use environment-specific credentials** - Don't use production credentials in development
- **Rotate credentials regularly** - Follow your organization's security policies
- **Limit API permissions** - Use credentials with minimum necessary permissions

## Extending This Example

### Adding More Question Types

To support additional question types like MultiSelect or Address, extend the `build_answer_object()` function:

```python
# For MultiSelect
if question_type == 'MultiSelect':
    # Parse comma-separated UUIDs
    option_uuids = [uuid.strip() for uuid in answer_value.split(',')]
    return {'multi_select': {'values': option_uuids}}

# For Address
if question_type == 'Address':
    # Parse JSON address object from CSV
    address_data = json.loads(answer_value)
    return {'address': address_data}
```

### Error Recovery with Retries

Add retry logic for transient failures:

```python
from time import sleep

def update_with_retry(access_token, environment, form_id, questions, max_retries=3):
    for attempt in range(max_retries):
        try:
            return update_form_questions(access_token, environment, form_id, questions)
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

### Progress Tracking

For large CSV files, add a progress bar:

```bash
pip install tqdm
```

```python
from tqdm import tqdm

for form_id, form_updates in tqdm(updates_by_form.items(), desc="Processing forms"):
    # Process updates...
```

## Additional Resources

- **Customer API Documentation:** Contact your Avela representative
- **Avela Developer Portal:** See other examples in this repository
- **Integration Support:** Contact your Avela integration support team

## License

MIT License - See LICENSE file for details
