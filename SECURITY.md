# Security Policy

## Supported Versions

We maintain the latest version of every example in this repository.

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| Older   | :x:                |

## Reporting a Vulnerability

Found a security problem in an example or in the documentation? Report it this way.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Email **[security@avela.org](mailto:security@avela.org)** instead, and include:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** of the vulnerability
- **Affected examples** or files
- **Suggested fix** (if you have one)

### What to Expect

1. **Acknowledgment**: We confirm we got it within 48 hours
2. **Assessment**: We judge the severity and impact
3. **Fix**: We build a patch or a workaround
4. **Disclosure**: We agree with you on when to make it public

### Response Timeline

- **Critical vulnerabilities**: Fixed within 7 days
- **High severity**: Fixed within 14 days
- **Medium/Low severity**: Fixed within 30 days

## Security Best Practices for Contributors

When contributing examples to this repository:

### ❌ Never Include

- API credentials (client IDs, secrets, tokens)
- Real email addresses or phone numbers
- Database passwords or connection strings
- Private keys or certificates
- Production URLs or endpoints
- Personal Identifiable Information (PII)
- Internal system information

### ✅ Always Include

- Credentials from the shared client, never a config file reader of your own
- Input validation examples
- Error handling patterns
- Rate limiting considerations
- Authentication best practices

### Code Security Checklist

- [ ] No hardcoded credentials
- [ ] Credentials come from `create_client()` or `resolve_credentials()`
- [ ] Input validation implemented
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies are up-to-date
- [ ] HTTPS used for all API calls
- [ ] No credential values printed, logged, or written to output files
- [ ] Token expiration handled
- [ ] Rate limiting respected

## Security Considerations for Users

When using examples from this repository:

### Credentials Management

- **Never commit** credentials to version control
- Use the **OS keychain** on a laptop and **environment variables** everywhere else
- Rotate credentials regularly
- Use different credentials for dev and prod, and keep them apart with profiles
- Give each set of credentials only the access it needs

### Separating Credentials With Profiles

One set of credentials for several clients makes it easy to run the right script
against the wrong data. Give each set a profile name instead:

```bash
python shared/python/setup_credentials.py --profile district-a
python avela_api_client.py --profile district-a
```

Each profile is its own keychain entry, so you can rotate or delete one without
touching the others. Every recipe prints a `Credentials:` line naming the
profile it used. Check it before you run anything that writes or deletes. Full
reference: [shared/python/README.md](shared/python/README.md).

### Credential Storage Options

Recipes get their credentials from `shared/python/avela_client.py`. It checks three sources in order and stops at the first with both an ID and a secret: arguments passed in code, environment variables, then the OS keychain. Environment variables come before the keychain so a server, container, or CI job can override what a developer stored on a laptop. `config.json` files are for non-secret settings only; credentials in one are ignored.

Best first:

| Option                | Best for                            |
| --------------------- | ----------------------------------- |
| OS keychain           | Recipes run on a laptop             |
| Environment variables | Servers, CI, containers, schedulers |

**OS keychain.** macOS Keychain, Windows Credential Manager, and the Linux Secret Service all encrypt what they store. They need someone logged in at a desktop, so they will not work on servers, in containers, or in CI. Every recipe installs `keyring`, so nothing extra is needed. Store credentials with:

```bash
python shared/python/setup_credentials.py
```

It asks for the values, so the secret never reaches your screen or your shell history.

**Environment variables.** Set `AVELA_CLIENT_ID`, `AVELA_CLIENT_SECRET`, and `AVELA_ENVIRONMENT`. Secret managers feed values in this way too, including AWS Secrets Manager, SSM Parameter Store, and 1Password `op run`.

### Rotate Secrets That Sat in Plain Text

Treat a client secret stored in a `config.json` as exposed. Files like that get backed up, synced to cloud storage, and pasted into tickets. If you have one:

1. Ask your Avela administrator for a new client secret
2. Store the new secret in the OS keychain or an environment variable
3. Remove the credentials from the file. Settings can stay

Full credential documentation: [`shared/python/README.md`](shared/python/README.md).

### API Usage

- **Validate inputs** before sending to API
- **Handle errors** without exposing sensitive details
- **Respect rate limits** to avoid service disruption
- **Log securely**: don't log tokens or sensitive data
- **Use HTTPS** always

### Webhook Security

- **Validate signatures** on incoming webhooks
- **Use HTTPS endpoints** only
- **Handle repeats safely** so a retried event is not applied twice
- **Rate limit** webhook endpoints
- **Verify event sources**

## Known Security Considerations

### OAuth2 Tokens

- Tokens expire after 24 hours
- The shared client keeps tokens in memory only and never writes them to disk
- Never write a token to a file, a log line, or a CSV export
- Refresh tokens automatically
- Revoke tokens when no longer needed

### API Rate Limits

- Wait longer after each retry (exponential backoff)
- Cache responses when appropriate
- Monitor usage to stay within limits
- Handle 429 responses gracefully

### Data Privacy

- Applicant data contains PII
- Follow data protection regulations (GDPR, FERPA, etc.)
- Set rules for how long you keep data
- Encrypt data at rest and in transit
- Log access for audit purposes

## Vulnerability Disclosure Policy

### Our Commitments

- We will respond to your report within 48 hours
- We will keep you informed of progress
- We will credit you for responsible disclosure (if desired)
- We will not pursue legal action for good-faith security research

### Your Responsibilities

- Give us reasonable time to fix the issue before public disclosure
- Make a good faith effort to avoid privacy violations
- Don't access or modify data beyond what's necessary to demonstrate the vulnerability
- Don't perform denial-of-service attacks

## Security Updates

When we fix security issues:

1. **Patch** the vulnerable code
2. **Update** the changelog
3. **Notify** affected users (if applicable)
4. **Document** lessons learned
5. **Thank** the reporter (if they consent)

## Contact

- **Security issues**: [security@avela.org](mailto:security@avela.org)
- **General support**: [help@avela.org](mailto:help@avela.org)
- **Documentation**: [API Reference](https://prod.api-docs.avela.dev/v2/index.html)

---

**Thank you for helping keep the Avela Integration Cookbook secure!** 🔒
