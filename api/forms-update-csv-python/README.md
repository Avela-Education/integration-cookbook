# Update Form Answers from CSV - Python

Update form answers in bulk by reading from a CSV file.

## Prerequisites

- **Python 3.10 or higher**
- **API Credentials** from Avela (client_id and client_secret)
- **Form IDs and Question Keys** you want to update

**macOS users:** If you haven't used Python before, install the Xcode Command Line Tools first:
```bash
xcode-select --install
```
A dialog appears. Click "Install" and wait for it to finish. This gives Python the compiler tools it needs to create virtual environments.

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

Set up your credentials, then prepare your CSV file.

**Environment options:**
- `dev` - Development environment
- `qa` - QA environment
- `uat` - UAT environment
- `prod` - Production environment

### 1. Store your credentials

On a laptop, store them once in your computer's keychain:

```bash
python ../../shared/python/setup_credentials.py
```

The helper asks for your client id, client secret, and environment, hides the secret as you type it, and stores it encrypted. Add `--show`, `--list`, or `--delete` to see or remove what is stored.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### 2. Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python form_update_client.py --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. See [shared/python/README.md](../../shared/python/README.md) for the full explanation.

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
- `question_type` - The type of question (FreeText, Email, PhoneNumber, Number, Date, SingleSelect, MultiSelect, Address)
- `answer_value` - The new answer value to set

**Note:** The `question_type` column is optional and defaults to "FreeText" if not provided.

## Usage

### Run the script

```bash
# Use the default credentials
python form_update_client.py

# Use a named profile
python form_update_client.py --profile district-a
```

### Expected Output

```
Authenticating with Avela API (prod)...
✓ Authentication successful!

✓ Read 3 updates from CSV file
Processing updates for 2 form(s)...

Form: e4c2f10d-...
  Submitting 2 question(s) to API... ✓

Form: f5d3e20e-...
  Submitting 1 question(s) to API... ✓

RESULTS: ✓ Successful: 3 | Failed: 0
```

## Question Types

| Type         | CSV Example                                        | Notes                                            |
|--------------|----------------------------------------------------|--------------------------------------------------|
| FreeText     | `internal1,FreeText,John Doe`                      | Default if type omitted                          |
| Email        | `contact,Email,john@example.com`                   | Must be valid email                              |
| PhoneNumber  | `phone,PhoneNumber,555-0123`                       |                                                  |
| Number       | `age,Number,42`                                    | Must be numeric                                  |
| Date         | `dob,Date,2024-03-15`                              | Format: YYYY-MM-DD                               |
| SingleSelect | `choice,SingleSelect,option-value`                 | Use option value (not label)                     |
| MultiSelect  | `choice,MultiSelect,val1,val2,val3`                | Comma-separated option values; empty clears      |
| Address      | `addr,Address,123 Main St\|Apt 2\|City\|ST\|12345` | Pipe-delimited: street1\|street2\|city\|state\|zip |

## Common Issues

### 401 Unauthorized Error

**Problem:** You receive a 401 error when trying to authenticate or update.

**Solution:**
- Verify your client id and client secret are correct in whichever source you set up
- Check where they came from. The script reports it as `client.credential_source`, so you can confirm an older source is not winning
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

- **Keep secrets out of files** - Credentials live in the keychain or environment variables, never in a file
- **Keep credentials secure** - In production, use environment variables or a secrets manager
- **Use environment-specific credentials** - Don't use production credentials in development
- **Rotate credentials regularly** - Follow your organization's security policies
- **Limit API permissions** - Use credentials with the fewest permissions that do the job

## Additional Resources

- [Other examples in this repository](../)
- Integration Support: Contact your Avela representative

---

## Extending This Example

### Adding More Question Types

To support additional question types, extend the `build_answer_object()` function in the script. See existing implementations for FreeText, Number, MultiSelect, and Address as examples.

### Adding Retry Logic

For production use, add retry logic for transient failures:

```python
from time import sleep


def update_with_retry(access_token, environment, form_id, questions, max_retries=3):
    for attempt in range(max_retries):
        try:
            return update_form_questions(access_token, environment, form_id, questions)
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                sleep(2**attempt)  # Exponential backoff
                continue
            raise
```

---

**Complexity Level:** Intermediate | **Language:** Python 3.10+ | **API Version:** v2
