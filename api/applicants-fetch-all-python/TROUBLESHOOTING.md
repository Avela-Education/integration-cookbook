# Troubleshooting

Common issues and solutions for the Fetch All Applicants script.

## "No credentials found"

**Problem:** No place the script looked held both a client id and a client secret. The error message lists both options.

**Solution:** set up any one of them.

```bash
# OS keychain (recommended on a laptop)
python ../../shared/python/setup_credentials.py

# Environment variables (recommended for servers, CI, and containers)
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod

```

Set both the id and the secret. If only one of the two is set, the script stops and says which one is missing.

## Keychain is locked or unavailable

**Problem:** The script cannot reach the keychain, so it cannot see your stored credentials. Common causes:

1. Dependencies not installed, run `pip install -r requirements.txt`
2. The keychain is locked and no one is there to unlock it
3. The script is running over SSH, in a container, or in CI, where there is no desktop session to unlock a keychain
4. Linux without a Secret Service program such as `gnome-keyring` or `kwallet`

**Solution:** on a laptop, unlock the keychain and run again. Anywhere without a desktop login, use environment variables instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables before the keychain, so they work even when the keychain holds old values.

## Profile has nothing stored

**Problem:** You ran with `--profile district-a` (or `AVELA_PROFILE=district-a`) and no credentials were found for it.

**Solutions:**
1. List what is actually stored: `python ../../shared/python/setup_credentials.py --list`
2. Store the profile: `python ../../shared/python/setup_credentials.py --profile district-a`
3. Check the spelling. Profile names become lowercase, and anything that is not a letter or a number turns into `-`, so `District A` becomes `district-a` and its environment variables are `AVELA_DISTRICT_A_CLIENT_ID` and `AVELA_DISTRICT_A_CLIENT_SECRET`
4. If the profile's credentials come from environment variables, use the names with the profile in them (`AVELA_DISTRICT_A_CLIENT_ID`, not `AVELA_CLIENT_ID`). A profile never reads the plain names, so a mistyped profile cannot run as the wrong client

## "Authentication failed"

**Problem:** Invalid credentials or wrong environment

**Solutions:**
1. Check where the credentials came from. The script reports it as `client.credential_source`, for example `keychain (avela-api:district-a)`, so you can confirm an older source is not winning
2. Verify the client id and secret in whichever source you set up
3. Confirm you're using the correct environment (usually `prod`)
4. Check for extra spaces or quotes in credentials
5. Contact your Avela administrator to verify credentials are active

## "No applicants found"

**Problem:** Query returned zero results

**Possible causes:**
1. You're using a test environment with no data
2. The `reference_ids` filter doesn't match any records
3. Your credentials don't have access to applicant data

**Solution:**
- Try option [1] to fetch all applicants (no filter)
- Verify the environment stored in whichever credential source you configured
- Check permissions with your administrator

## Module not found errors

**Problem:** Dependencies not installed

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Virtual environment not activating

**Problem:** `source venv/bin/activate` doesn't work

### Windows (PowerShell)
```powershell
# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate:
venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)
```bash
venv\Scripts\activate.bat
```

### macOS/Linux
```bash
# Make sure you're in the correct directory
cd api/applicants-fetch-all-python

# Try with full path
source ./venv/bin/activate
```

## Wrong Python version

**Problem:** Virtual environment using wrong Python version

**Solution:**
```bash
# Remove old virtual environment
rm -rf venv  # Windows: rmdir /s venv

# Create with specific Python version
python3.10 -m venv venv

# Activate and reinstall
source venv/bin/activate
pip install -r requirements.txt
```

## macOS: "No developer tools found"

**Problem:** Xcode Command Line Tools not installed

**Solution:**
```bash
xcode-select --install
```
A dialog appears. Click "Install" and wait for it to finish, then create your virtual environment again.
