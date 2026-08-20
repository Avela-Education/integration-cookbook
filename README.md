# Integration Cookbook 🚀

> Production-ready integration patterns for the Avela Education Platform

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![API Version](https://img.shields.io/badge/API-v2-green.svg)](https://prod.api-docs.avela.dev/v2/index.html)

## 🎯 Quick Start

### 🔑 Store Your Credentials First

Do this once. Every recipe reads your credentials from here, so you never paste a secret into a file a recipe reads.

**On a laptop, use your OS keychain:**

```bash
git clone https://github.com/Avela-Education/integration-cookbook.git
cd integration-cookbook

pip install -e shared/python
python shared/python/setup_credentials.py
```

The helper asks for your client ID and secret. Nothing lands in your shell history or on disk in plaintext.

Starting with a recipe instead? Its `pip install -r requirements.txt` covers the same install, so go straight to `setup_credentials.py`.

**On a server, in a container, or in CI, use environment variables:**

```bash
export AVELA_CLIENT_ID='your_client_id'
export AVELA_CLIENT_SECRET='your_client_secret'
export AVELA_ENVIRONMENT='prod'
```

Environment variables beat the keychain, so a deployed job always uses what the deployment gives it. For several client profiles, see [shared/python/README.md](shared/python/README.md).

### 🔌 Fetch All Applicants (Python)
Retrieve and export applicant data with automatic pagination

```bash
cd api/applicants-fetch-all-python

# Set up and run
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python avela_api_client.py
```

### 📊 Update Forms from CSV (Python)
Bulk update form answers by reading from a CSV file

```bash
cd api/forms-update-csv-python

# Set up and run
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python form_update_client.py
```

## 📚 Integration Methods

| Method                | Use When              | Best For                | Example                                              |
| --------------------- | --------------------- | ----------------------- | ---------------------------------------------------- |
| **Customer API v2**   | Real-time data access | Custom apps, dashboards | [Fetch applicants](api/applicants-fetch-all-python/) |
| **CSV Import/Export** | Bulk operations       | Data migration, reports | [Update forms](api/forms-update-csv-python/)         |
| **Webhooks**          | Event-driven          | Real-time notifications | Coming soon                                          |
| **Third-party Tools** | No-code integration   | Zapier, Make.com        | Coming soon                                          |

## 🗂️ Browse by Category

### API Integration
Read and write Avela data from your own code. Browse every recipe in the [api/](api/) folder.

**Available Recipes:**
- [**Fetch All Applicants (Python)**](api/applicants-fetch-all-python/) retrieves and exports applicant data with automatic pagination
- [**Update Forms from CSV (Python)**](api/forms-update-csv-python/) bulk updates form answers by reading from a CSV file
- [**Download Form Files (Python)**](api/forms-download-files-python/) batch downloads file attachments from forms
- [**Update Offer Status (Python)**](api/offers-update-status-python/) bulk accepts or declines offers from a CSV file

## 🛠️ Prerequisites

You need:

1. **Avela API Credentials**
   - Client ID and Client Secret
   - Existing customers: email [help@avela.org](mailto:help@avela.org)
   - New to Avela? [Contact us](https://avela.org/contact)

2. **Development Environment**
   - Python 3.10+ or Node.js 16+ (depending on examples)
   - Git for cloning the repository
   - Text editor or IDE

3. **Basic Knowledge**
   - REST APIs and HTTP
   - JSON data format
   - OAuth2 authentication (helpful but not required)

## 🔑 Authentication

All API examples use the OAuth2 client credentials flow:
- Avela gives you a Client ID and Client Secret
- Tokens are valid for 24 hours
- Every request carries `Bearer {token}` in its Authorization header

Recipes never ask you where your credentials live. The shared client checks three places in order and uses the first that has both an ID and a secret:

| Order | Source                | Details                                                       |
| ----- | --------------------- | ------------------------------------------------------------- |
| 1     | Arguments in code     | Passed to `AvelaClient()`                                     |
| 2     | Environment variables | `AVELA_CLIENT_ID`, `AVELA_CLIENT_SECRET`, `AVELA_ENVIRONMENT` |
| 3     | OS keychain           | Service `avela-api`, populated by `setup_credentials.py`      |

Credentials in a `config.json` from an earlier version of this cookbook are no longer used; a note tells you when one is found. Move those credentials into the keychain or your environment, then rotate the secret. Treat any secret that has sat in a plaintext file as exposed.

Working with more than one Avela client? Store each set under a profile:

```bash
python shared/python/setup_credentials.py --profile district-a

# Then pick one per run, either way
python avela_api_client.py --profile district-a
AVELA_PROFILE=district-a python avela_api_client.py
```

See the [Security Guide](SECURITY.md) for best practices and [shared/python/README.md](shared/python/README.md) for the full credential reference.

## 🤖 AI Assistant Setup Help

Using an AI assistant (ChatGPT, Claude, Copilot, etc.) to help with setup? See [AGENT.md](AGENT.md) for instructions that keep your credentials secure.

**Example prompt:**
```
Looking at this cookbook, can you download documents for the form IDs listed at
api/forms-download-files-python/form_ids.txt? Please be descriptive at the end
of the steps you took to do this in case I want to do it manually. Let me know
what files were downloaded and where they are. Be sure to read AGENT.md warnings.
```

## 📖 Documentation & Resources

- [**API Reference**](https://prod.api-docs.avela.dev/v2/index.html) for the complete API documentation
- [**Webhook Events**](https://help.avela.org/hc/en-us/articles/30566811184909-Webhooks) for the events you can subscribe to
- [**Rate Limits**](shared/python/README.md#rate-limits) for API usage limits
- **Support:** email [help@avela.org](mailto:help@avela.org)

## 🤝 Contributing

Contributions are welcome. You can:

- 🐛 Report a bug
- 💡 Request a new example
- 📝 Improve documentation
- 🔧 Submit a new integration pattern

Our [Contributing Guide](CONTRIBUTING.md) covers:
- Code style guidelines
- Example standards and templates
- Pull request process
- Testing requirements

## 💬 Support & Community

- **📧 Email:** [help@avela.org](mailto:help@avela.org)
- **🐛 Bug Reports:** [GitHub Issues](https://github.com/Avela-Education/integration-cookbook/issues)
- **📚 Documentation:** [API Reference](https://prod.api-docs.avela.dev/v2/index.html)

## 📜 License

This project uses the MIT License. See the [LICENSE](LICENSE) file for details.

## Roadmap

Our [Roadmap](ROADMAP.md) lists planned examples and future features.

Want to request a new example? [Create an issue](https://github.com/Avela-Education/integration-cookbook/issues/new?template=example_request.md).
