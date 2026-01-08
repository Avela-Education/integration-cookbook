# Troubleshooting

Common issues and solutions for the Fetch All Applicants script.

## "Configuration file not found"

**Problem:** `config.json` doesn't exist

**Solution:**
```bash
cp config.example.json config.json
# Edit config.json with your credentials
```

## "Authentication failed"

**Problem:** Invalid credentials or wrong environment

**Solutions:**
1. Verify `client_id` and `client_secret` in `config.json`
2. Confirm you're using the correct environment (usually `prod`)
3. Check for extra spaces or quotes in credentials
4. Contact your Avela administrator to verify credentials are active

## "No applicants found"

**Problem:** Query returned zero results

**Possible causes:**
1. You're using a test environment with no data
2. The `reference_ids` filter doesn't match any records
3. Your credentials don't have access to applicant data

**Solution:**
- Try option [1] to fetch all applicants (no filter)
- Verify the correct environment in config
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
A dialog will appear - click "Install" and wait for completion. Then retry creating your virtual environment.
