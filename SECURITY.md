# Security Policy

## Supported Versions

We actively maintain and support the latest versions of examples in this repository.

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| Older   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in any of the examples or documentation, please report it responsibly:

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please email: **[security@avela.org](mailto:security@avela.org)**

Include the following information:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** of the vulnerability
- **Affected examples** or files
- **Suggested fix** (if you have one)

### What to Expect

1. **Acknowledgment**: We'll confirm receipt within 48 hours
2. **Assessment**: We'll evaluate the severity and impact
3. **Fix**: We'll work on a patch or mitigation
4. **Disclosure**: We'll coordinate responsible disclosure

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

- Configuration templates (`.example` files)
- Environment variable documentation
- Input validation examples
- Error handling patterns
- Rate limiting considerations
- Authentication best practices

### Code Security Checklist

- [ ] No hardcoded credentials
- [ ] Input validation implemented
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies are up-to-date
- [ ] HTTPS used for all API calls
- [ ] Secrets managed via environment variables
- [ ] Token expiration handled
- [ ] Rate limiting respected

## Security Considerations for Users

When using examples from this repository:

### Credentials Management

- **Never commit** credentials to version control
- Use **environment variables** or secure vaults
- Rotate credentials regularly
- Use different credentials for dev/prod
- Implement least-privilege access

### API Usage

- **Validate inputs** before sending to API
- **Handle errors** without exposing sensitive details
- **Respect rate limits** to avoid service disruption
- **Log securely** - don't log tokens or sensitive data
- **Use HTTPS** always

### Webhook Security

- **Validate signatures** on incoming webhooks
- **Use HTTPS endpoints** only
- **Implement idempotency** to handle retries
- **Rate limit** webhook endpoints
- **Verify event sources**

## Known Security Considerations

### OAuth2 Tokens

- Tokens expire after 24 hours
- Store tokens securely (never in plaintext files)
- Implement automatic refresh logic
- Revoke tokens when no longer needed

### API Rate Limits

- Implement exponential backoff
- Cache responses when appropriate
- Monitor usage to stay within limits
- Handle 429 responses gracefully

### Data Privacy

- Applicant data contains PII
- Follow data protection regulations (GDPR, FERPA, etc.)
- Implement data retention policies
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
- **General support**: [api-support@avela.org](mailto:api-support@avela.org)
- **Documentation**: [docs.avela.org](https://docs.avela.org)

---

**Thank you for helping keep the Avela Integration Cookbook secure!** 🔒
