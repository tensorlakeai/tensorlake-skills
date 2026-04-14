<!--
Source:
  - https://docs.tensorlake.ai/platform/webhooks/overview.md
  - https://docs.tensorlake.ai/platform/webhooks/configuration.md
  - https://docs.tensorlake.ai/platform/webhooks/signature-verification.md
  - https://docs.tensorlake.ai/platform/webhooks/payloads/document-ingestion.md
  - https://docs.tensorlake.ai/platform/webhooks/payloads/workflows.md
  - https://docs.tensorlake.ai/platform/webhooks/testing.md
  - https://docs.tensorlake.ai/platform/access-control.md
  - https://docs.tensorlake.ai/platform/authentication.md
  - https://docs.tensorlake.ai/platform/eu-data-residency.md
  - https://docs.tensorlake.ai/platform/billing.md
  - https://docs.tensorlake.ai/platform/playground/overview.md
  - https://docs.tensorlake.ai/platform/playground/sample-documents.md
  - https://docs.tensorlake.ai/platform/security.md
  - https://docs.tensorlake.ai/platform/sso.md
SDK version: tensorlake 0.4.42
Last verified: 2026-04-08
-->

# TensorLake Platform Reference

## Authentication

### API Key Management

API keys are project-scoped credentials with format `tl_apiKey_*`. They have the same permissions as project members.

```python
from tensorlake.documentai import DocumentAI

doc_ai = DocumentAI(api_key="tl_apiKey_...")
```

**REST API:**
```
Authorization: Bearer <token>
```

**Key characteristics:**
- Project-specific only; separate keys required per project
- No built-in expiration; active until manually deleted
- Cannot restrict access to specific endpoints
- 401 Unauthorized = invalid, deleted, or malformed key

**Security best practices:**
- Store keys in environment variables or credential management systems
- Never hardcode or commit keys to version control
- Immediately revoke compromised keys and generate replacements

---

## Access Control

### Hierarchy

TensorLake uses a two-tier model: **Organizations** contain **Projects**.

### Organization Roles

| Role | Capabilities |
|------|-------------|
| **Org Admin** | Create projects, invite users, manage roles, access all projects automatically |
| **Org Member** | View member lists, access only explicitly assigned projects |

### Project Roles

| Role | Capabilities |
|------|-------------|
| **Project Admin** | Add/remove members, change roles, create API keys and webhooks |
| **Project Member** | View and interact with project resources (read-only for most) |

API keys have the same permissions as Project Members.

**Best practices:**
- Organize projects by resource sensitivity, not team structure
- Apply principle of least privilege
- Audit memberships and rotate API keys periodically
- Invitations expire after 7 days

---

## Webhooks

Webhooks notify your endpoints of Document Ingestion and Workflow status changes. Managed through Svix.

### Setup

1. Navigate to project -> Webhooks tab
2. Provide webhook name and endpoint URL
3. Select event types to monitor

**Security:** Webhook deliveries are cross-origin POSTs without a session cookie, so frameworks that enable CSRF protection by default will reject them. Do **not** disable CSRF protection globally. Instead:

1. **Exempt only the webhook route** from CSRF middleware (e.g., Django `@csrf_exempt`, Rails `skip_before_action :verify_authenticity_token, only: [:webhook]`, Express-style per-route exclusion).
2. **Verify the Svix signature** on every request using the signing secret from the webhook settings — this is what actually authenticates the payload. Reject any request whose signature does not validate.

### Event Types

| Event | Trigger |
|-------|---------|
| `tensorlake.document_ingestion.job.created` | Parsing request received and initiated |
| `tensorlake.document_ingestion.job.failed` | Parsing job encountered failure |
| `tensorlake.document_ingestion.job.completed` | Parsing job succeeded |

### Payload Examples

**Job Created:**
```json
{
  "job_id": "parse_XXX",
  "status": "pending",
  "created_at": "2023-10-01T12:00:00Z"
}
```

**Job Failed:**
```json
{
  "job_id": "parse_XXX",
  "status": "failure",
  "error": "Error message describing the failure",
  "created_at": "2023-10-01T12:00:00Z",
  "finished_at": "2023-10-01T12:05:00Z"
}
```

**Job Completed:**
```json
{
  "job_id": "parse_XXX",
  "status": "successful",
  "created_at": "2023-10-01T12:00:00Z",
  "finished_at": "2023-10-01T12:05:00Z",
  "usage": {
    "pages_parsed": 10,
    "extraction_input_tokens_used": 0,
    "extraction_output_tokens_used": 0,
    "ocr_input_tokens_used": 0,
    "ocr_output_tokens_used": 0,
    "signature_detected_pages": 0,
    "strikethrough_detected_pages": 0,
    "summarization_input_tokens_used": 0,
    "summarization_output_tokens_used": 0
  }
}
```

**Workflow Completion:**
```json
{
  "workflow_name": "workflow_XXXX",
  "invocation_id": "invocation_XXXX",
  "fn_status": {
    "fn_A": "success",
    "fn_B": "failure"
  }
}
```

### Signature Verification

Each webhook has a unique secret (found in webhook details on the dashboard).

**Verification methods:**
- **Automated (recommended):** Use Svix libraries for payload validation
- **Manual:** Extract signature from `svix-signature` header, compute expected HMAC, compare values

Unverified endpoints risk forged requests.

### Testing

Use the Webhooks tab UI to trigger test payloads by selecting an event type.

---

## EU Data Residency

TensorLake provides EU-region API services for data residency compliance.

**EU endpoint:** `https://api.eu.tensorlake.ai/`

### Configuration

```python
from tensorlake.documentai import DocumentAI, Region

# Document Ingestion
doc_ai = DocumentAI(api_key="YOUR_API_KEY", region=Region.EU)
```

```python
from tensorlake.applications import application, function
from tensorlake.documentai import Region

# Applications / Workflows — pass region to @application()
@application(region="eu-west-1")
@function()
def my_workflow(data: str) -> str:
    ...
```

**Key points:**
- A single API key works across both US and EU regions
- Webhook support is available in the EU region
- Set `region=Region.EU` in SDK constructors
