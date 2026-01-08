# AI Assistant Instructions

Instructions for AI assistants (ChatGPT, Claude, Copilot, Cursor, etc.) helping users set up Avela integration recipes.

---

## Why This Matters

Avela is an education platform that processes **K-12 student enrollment data**. This includes sensitive information about children and families that is protected under **FERPA** (Family Educational Rights and Privacy Act) and other privacy regulations.

Data exposed in AI chat sessions may be logged, stored, or used for model training. Protecting this information is not optional—it's a legal and ethical requirement.

---

## CRITICAL: Credential Security

> **NEVER ask users to share API credentials (client_id, client_secret) in this chat.**
>
> Credentials shared in chat may be logged, stored, or exposed. Always direct users to enter credentials directly into their local config.json file.

### Safe Credential Setup

When helping users configure credentials, use this workflow:

```
1. Copy the template:    cp config.example.json config.json
2. Open in editor:       Open config.json in your text editor
3. Enter credentials:    Type your client_id and client_secret directly
4. Save the file:        Save and close config.json
```

**DO NOT:**
- Ask users to paste credentials into this chat
- Offer to "help fill in" the config file with their credentials
- Request credentials to "verify" or "validate" them

**DO:**
- Explain where to find credentials (Avela administrator)
- Help troubleshoot authentication errors without seeing credentials
- Guide users through the config.json structure

---

## CRITICAL: No Personal Data (PII)

> **NEVER expose personally identifiable information (PII) in this chat.**
>
> This includes:
> - Names (first, middle, last)
> - Birth dates
> - Social Security numbers
> - Addresses
> - Email addresses
> - Phone numbers
>
> Data in chat may be logged, stored, or used for training. Avela handles sensitive student and family data that must remain confidential.

**PII protection is bidirectional:**
1. **Users should not paste PII** into this chat
2. **AI assistants should not pull PII** from the API and display it in chat

**DO NOT:**
- Ask users to paste CSV data containing real applicant information
- Request sample data with actual names, emails, or other PII
- Offer to help "debug" by looking at real data
- Run API scripts and display the returned applicant/form data
- Read or display the contents of exported CSV files containing real data

**DO:**
- Use placeholder data for examples (e.g., "John Doe", "test@example.com")
- Ask users to describe the *structure* of their data, not the content
- Help troubleshoot based on error messages, not actual data values
- Confirm scripts ran successfully without showing the actual output data
- Guide users to inspect exported files themselves

---

## Setup Workflow

Help users through these steps:

### 1. Navigate to Recipe Directory
```bash
cd integration-cookbook/api/{recipe-name}
```

Available recipes:
- `applicants-fetch-all-python/` - Fetch and export applicant data
- `forms-update-csv-python/` - Bulk update form answers from CSV
- `forms-download-files-python/` - Download file attachments from forms

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Credentials (User Does This Manually)
```bash
cp config.example.json config.json
# User opens config.json and enters credentials directly
```

### 5. Run the Script
```bash
python {script_name}.py
```

---

## Recipe-Specific Guidance

### Fetch All Applicants
- **Script:** `avela_api_client.py`
- **Output:** CSV file with applicant data
- **Options:** Can filter by reference IDs when prompted

### Update Forms from CSV
- **Script:** `form_update_client.py`
- **Requires:** CSV file with form updates (form_id, question_key, question_type, answer_value)
- **Sample:** See `sample_updates.csv` for format

### Download Form Files
- **Script:** `download_form_files.py`
- **Requires:** Text file with form IDs (one per line)
- **Output:** Files organized by form_id/question_key/

---

## Troubleshooting

Help diagnose these common issues:

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| "Configuration file not found" | config.json missing | `cp config.example.json config.json` |
| "Authentication failed" | Wrong credentials or environment | Verify environment value (prod, qa, etc.), check for typos |
| "ModuleNotFoundError" | Dependencies not installed | Activate venv, run `pip install -r requirements.txt` |
| "No applicants found" | Wrong environment or no data | Confirm correct environment, check API access |
| "Invalid question key" | Typo in CSV | Question keys are case-sensitive |

### Authentication Errors (Without Seeing Credentials)

If a user reports authentication failures, ask:
1. "What environment are you using? (prod, qa, uat, dev)"
2. "Did you copy the credentials exactly without extra spaces?"
3. "Are the credentials from your Avela administrator or a different source?"

**Never ask to see the actual credential values.**

---

## Environment Reference

| Environment | When to Use |
|-------------|-------------|
| `prod` | Production data (most common) |
| `qa` | QA testing |
| `uat` | User acceptance testing |
| `dev` | Development |

Most users should use `prod` unless specifically testing.

---

## Additional Resources

- Each recipe has a detailed README.md with full documentation
- See [SECURITY.md](SECURITY.md) for security best practices
- See [CONTRIBUTING.md](CONTRIBUTING.md) for adding new recipes
