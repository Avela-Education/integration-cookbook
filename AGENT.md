# AI Assistant Instructions

Instructions for AI assistants (ChatGPT, Claude, Copilot, Cursor, etc.) helping users set up Avela integration recipes.

---

## Why This Matters

Avela is an education platform that handles **K-12 student enrollment data**: sensitive information about children and families, protected by **FERPA** (Family Educational Rights and Privacy Act) and other privacy laws.

Anything typed into an AI chat may be logged, stored, or used to train a model. Protecting this data is a legal and ethical requirement, not a preference.

---

## CRITICAL: Credential Security

> **NEVER ask users to share API credentials (client_id, client_secret) in this chat.**
>
> Credentials shared in chat may be logged, stored, or exposed. Tell users to store them in their OS keychain or in environment variables, and never to show you the values.

### Safe Credential Setup

The user runs this themselves, once the recipe's requirements are installed. It asks for the values, so the secret never appears in the terminal, in shell history, or in this chat:

```bash
python shared/python/setup_credentials.py
```

The keychain works out of the box on a laptop. On a server, in a container, or in CI, there is no keychain to unlock, so the user sets environment variables instead:

```bash
export AVELA_CLIENT_ID='...'
export AVELA_CLIENT_SECRET='...'
export AVELA_ENVIRONMENT='prod'
```

Recipes find credentials on their own, checking arguments, then environment variables, then the keychain. There is no file for you to create or fill in, and credentials in a `config.json` are ignored.

**DO NOT:**
- Ask users to paste credentials into this chat
- Offer to "help fill in" a config file with their credentials
- Request credentials to "verify" or "validate" them
- Read, print, or copy the contents of any credential file or keychain entry
- Put a client secret on a command line, where it lands in shell history

**DO:**
- Explain where to find credentials (Avela administrator)
- Point users at `setup_credentials.py` and let them type the values into its prompt
- Help troubleshoot authentication errors without seeing credentials
- Treat a credential the user has already put in a plain text file as exposed, and suggest rotating it

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
> Data in chat may be logged, stored, or used for training. Avela handles student and family data that must stay confidential.

**PII protection runs both ways:**
1. **Users should not paste PII** into this chat
2. **AI assistants should not pull PII** from the API and show it in chat

**DO NOT:**
- Ask users to paste CSV data containing real applicant information
- Request sample data with actual names, emails, or other PII
- Offer to help "debug" by looking at real data
- Run API scripts and display the applicant or form data they return
- Read or display the contents of exported CSV files containing real data

**DO:**
- Use made up data for examples (for example "John Doe", "test@example.com")
- Ask users to describe the *structure* of their data, not the content
- Troubleshoot from error messages, not from actual data values
- Confirm scripts ran without showing the data they produced
- Guide users to open exported files themselves

---

## Setup Workflow

Help users through these steps:

### 1. Navigate to Recipe Directory
```bash
cd integration-cookbook/api/{recipe-name}
```

Available recipes:
- `applicants-fetch-all-python/` - Fetch and export applicant data with pagination
- `forms-update-csv-python/` - Bulk update form answers from a CSV file
- `forms-download-files-python/` - Batch download file attachments from forms
- `offers-update-status-python/` - Bulk accept or decline offers from a CSV file
- `register-forms-find-school-python/` - Map every register form to its school
- `form-school-tags-import-python/` - Bulk import form school tags from a CSV file

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
python ../../shared/python/setup_credentials.py
```
The user types the client ID and secret into the prompt. Do not offer to run this for them, and do not ask what they entered.

Whenever a user mentions several districts, schools, or environments, suggest
giving each set of credentials a profile name:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python ../../shared/python/setup_credentials.py --profile district-b
```

They answer the prompt once per profile. `--list` shows what is stored, without
revealing any secret.

### 5. Run the Script
```bash
python {script_name}.py

# ...or, when the user has profiles, name the client to use
python {script_name}.py --profile district-a
```

A profile name picks that client everywhere: its keychain entry
(`avela-api:district-a`), its environment variables (`AVELA_DISTRICT_A_CLIENT_ID`),
`AVELA_PROFILE=district-a`
sets a default for the whole shell session, and `--profile` beats it for one run.

Before a user runs anything that writes or deletes data, ask them to check that
the `Credentials:` line names the client they expect. Switching clients is a one
word change, so the right script can easily hit the wrong district.

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

| Error                             | Likely Cause                     | Solution                                                                       |
| --------------------------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| "No Avela API credentials found"  | Nothing stored yet               | User runs `python shared/python/setup_credentials.py` or exports the env vars  |
| "No Avela API credentials found"  | Dependencies not installed       | Activate venv, run `pip install -r requirements.txt`                           |
| "No Avela API credentials found"  | Profile name has nothing stored  | Run `setup_credentials.py --list` to see stored profiles, check the spelling   |
| Right script, wrong client's data | Wrong profile selected           | Check the `Credentials:` line, and whether `AVELA_PROFILE` is set in the shell |
| "Authentication failed"           | Wrong credentials or environment | Verify environment value (prod, qa, etc.), check for typos                     |
| "ModuleNotFoundError"             | Dependencies not installed       | Activate venv, run `pip install -r requirements.txt`                           |
| "No applicants found"             | Wrong environment or no data     | Confirm correct environment, check API access                                  |
| "Invalid question key"            | Typo in CSV                      | Question keys are case-sensitive                                               |

### Authentication Errors (Without Seeing Credentials)

If a user reports authentication failures, ask:
1. "What environment are you using? (prod, qa, uat, dev)"
2. "Did you copy the credentials exactly without extra spaces?"
3. "Are the credentials from your Avela administrator or a different source?"

Every recipe prints a `Credentials: ...` line at startup naming where it got them, for example `Credentials: environment` or `Credentials: keychain (avela-api:district-a)`. It never contains a secret, so it is safe to ask for, and it tells you whether the recipe used the credentials the user thinks it did.

`python shared/python/setup_credentials.py --show` gives more detail. It never prints the secret, but it does print the client ID, so ask only for the environment and whether the secret reads as set.

**Never ask to see the actual credential values.**

---

## Environment Reference

| Environment | When to Use                   |
| ----------- | ----------------------------- |
| `prod`      | Production data (most common) |
| `qa`        | QA testing                    |
| `uat`       | User acceptance testing       |
| `dev`       | Development                   |

Most users should use `prod` unless they are testing.

---

## Lessons Learned

### OAuth2 Audience Format

The `audience` parameter must end in `/v1/graphql`:

```python
# Correct audience format
audience = f'https://{env}.api.apply.avela.org/v1/graphql'  # For non-prod
audience = 'https://api.apply.avela.org/v1/graphql'         # For prod
```

Without that suffix, authentication fails with:
```
{"error":"access_denied","error_description":"Service not enabled within domain: ..."}
```

---

## Additional Resources

- Each recipe has a detailed README.md with full documentation
- See [SECURITY.md](SECURITY.md) for security best practices
- See [CONTRIBUTING.md](CONTRIBUTING.md) for adding new recipes
