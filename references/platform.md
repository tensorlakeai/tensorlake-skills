<!--
Source:
  - https://docs.tensorlake.ai/platform/authentication.md
  - https://docs.tensorlake.ai/platform/access-control.md
  - https://docs.tensorlake.ai/platform/webhooks/overview.md
  - https://docs.tensorlake.ai/platform/webhooks/configuration.md
  - https://docs.tensorlake.ai/platform/webhooks/events.md
  - https://docs.tensorlake.ai/platform/webhooks/signature-verification.md
  - https://docs.tensorlake.ai/platform/webhooks/testing.md
  - https://docs.tensorlake.ai/platform/eu-data-residency.md
  - https://docs.tensorlake.ai/platform/billing.md
  - https://docs.tensorlake.ai/platform/security.md
  - https://docs.tensorlake.ai/platform/sso.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Platform Reference

Account, auth, access control, lifecycle webhooks, EU endpoints, security, and SSO.

> **Scope change since earlier versions of this snapshot.** The Document Ingestion / Document AI product, the integrations pages (LangChain, Chroma, Qdrant, Databricks, MotherDuck), and the Playground are **no longer in the Tensorlake docs**, and neither are the old `tensorlake.documentai` APIs or the `document_ingestion.job.*` webhook events. Webhooks now cover **sandbox, application, and application-request** lifecycle events. Do not suggest `from tensorlake.documentai import DocumentAI` or `Region` — those symbols are not in the current docs.

## Table of Contents

- [Authentication](#authentication)
- [Access Control](#access-control)
- [Webhooks](#webhooks)
  - [Configure a Destination](#configure-a-destination)
  - [Delivery Contract](#delivery-contract)
  - [Common Envelope](#common-envelope)
  - [Event Catalog](#event-catalog)
  - [Signature Verification](#signature-verification)
  - [Testing](#testing)
- [EU Endpoints](#eu-endpoints)
- [Billing](#billing)
- [Security](#security)
- [Single Sign-On (SSO)](#single-sign-on-sso)

## Authentication

You need a Tensorlake Cloud account ([cloud.tensorlake.ai](https://cloud.tensorlake.ai)) to call the APIs from the Python SDK, the `tensorlake` npm package, a generated TypeScript client, or the REST API directly.

### API keys

API keys are **project-specific** credentials with the **same permissions as a project member**. Every Tensorlake API key starts with `tl_apiKey_*`.

Create one: Tensorlake Dashboard → select the project → create an API key.

| Characteristic | Detail |
|---|---|
| Scope | Project-specific only. **API keys cannot have organization-level permissions.** Separate keys are required per project. |
| Expiration | No explicit expiration; active until deleted. |
| Endpoint restriction | Not supported — keys inherit project-member permissions. |
| `401 Unauthorized` | Invalid key, deleted key, or a key not correctly supplied as a Bearer token. Verify the key exists in the expected project, then check format and header structure. |

**Environment variable:**

```bash
export TENSORLAKE_API_KEY=your-api-key-here
```

**Python:**

```python
from tensorlake.sandbox import Sandbox   # sandbox pages use this import
sandbox = Sandbox.create()               # auth from `tl login` or TENSORLAKE_API_KEY
```

The platform authentication page shows an explicit-key variant, `from tensorlake import Sandbox` with `Sandbox.create(api_key=API_KEY)`. Prefer the env-var / `tl login` form used throughout the sandbox docs.

**TypeScript:**

```bash
npm install tensorlake
export TENSORLAKE_API_KEY=your-api-key-here
```

```typescript
import { Sandbox } from "tensorlake";

const sandbox = Sandbox.create({ apiKey: process.env.TENSORLAKE_API_KEY });
```

Assumes Node.js 18+, Bun, or Deno so `fetch` is global. The npm package covers sandboxes plus cloud/application APIs.

**REST:**

```bash
curl --request POST \
  --url https://api.tensorlake.ai/sandboxes \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json'
```

**CLI:** `tl login` (user-level auth). Note that `TENSORLAKE_API_KEY` **takes precedence over `tl login`**, which matters for user-only commands such as `tl sbx ssh keys`.

**Rotation:** create a new key, update your applications, then delete the old key — no downtime. If a key is compromised, delete it immediately and generate a new one. Store keys in environment variables or a credential manager; never hardcode or commit them.

Git repository access uses a **separate, short-lived credential** minted from your CLI/API credential — see [volumes_and_git.md](volumes_and_git.md#authentication-and-credentials). For enterprise SSO see [below](#single-sign-on-sso).

## Access Control

Two-tier hierarchy: **Organizations** contain **Projects**. Organizations have their own members and two roles (admin, member). Projects are containers for resources requiring similar access control — organize by **resource sensitivity and access requirements, not team structure**.

**Membership rule:** project membership is tied to organization membership. A user must be a member of an organization before being added to any project within it.

**API keys** operate exclusively at the project level with project-member permissions: they can access project resources and make API calls within project scope, but **cannot perform administrative actions**. Ideal for service accounts, automated processes, and integrations.

### Organization Management Permissions

| Permission | Org Admin | Org Member | Project Admin | Project Member | API Key |
|---|:-:|:-:|:-:|:-:|:-:|
| Create new projects | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite users to organization | ✅ | ❌ | ❌ | ❌ | ❌ |
| View organization members | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage organization member roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| Remove members from organization | ✅ | ❌ | ❌ | ❌ | ❌ |

### Project Access Control Permissions

| Permission | Org Admin | Org Member | Project Admin | Project Member | API Key |
|---|:-:|:-:|:-:|:-:|:-:|
| Access all projects automatically | ✅ | ❌ | ❌ | ❌ | ❌ |
| Add organization members to a project | ✅ | ❌ | ✅ | ❌ | ❌ |
| Remove members from a project | ✅ | ❌ | ✅ | ❌ | ❌ |
| Change project member roles | ✅ | ❌ | ✅ | ❌ | ❌ |
| View projects they are members of | ✅ | ✅ | ✅ | ✅ | N/A |

### Resource Access Permissions

| Permission | Org Admin | Org Member | Project Admin | Project Member | API Key |
|---|:-:|:-:|:-:|:-:|:-:|
| View project resources | ✅ | ❌ | ✅ | ✅ | ✅ |
| Manage project resources | ✅ | ❌ | ✅ | ❌ | ❌ |
| Create API keys for a project | ✅ | ❌ | ✅ | ❌ | ❌ |
| Create Webhooks for a project | ✅ | ❌ | ✅ | ❌ | ❌ |

Organization and project roles are **independent** — an org member can be a project admin for specific projects. Org admins have full access to every project in the organization whether or not they are explicit project members, and are the only role that can create projects, invite users, manage org roles, remove org members, and configure/enforce SSO. Project admins can add/remove project members and change project member roles, but cannot invite new users to the organization.

**Invitations.** Only org admins can create them. The admin specifies the invitee's email, organization role, and a default project plus project role. The invitee gets an emailed link; the account email must match the invitation email. **Invitations expire 7 days after creation.**

**Best practices:** create projects based on resource sensitivity and access requirements; group resources commonly accessed together; apply least privilege; audit project membership regularly (especially on role changes and departures); rotate API keys periodically.

## Webhooks

Tensorlake webhooks send **signed HTTPS notifications** when sandboxes, applications, and application requests change state — so you can react to lifecycle changes without polling. Each webhook belongs to **one project** and receives only that project's events, and only the event types selected for that destination. Delivery and signing are handled by **Svix**.

| Resource | Events |
|---|---|
| Sandbox | Created, running, suspended, resumed, terminated, failed |
| Application | Created, updated, deleted |
| Application request | Created, completed, failed |

### Configure a Destination

Prerequisites: a Tensorlake Cloud organization and project, **organization-admin or project-admin access**, and a public HTTPS endpoint accepting `POST`.

1. In [Tensorlake Cloud](https://cloud.tensorlake.ai), select the project that produces the events, then select **Webhooks**.
2. **Create webhook** → provide a **name** and an **absolute HTTPS endpoint URL without embedded credentials**.
3. Select one or more sandbox / application / application-request lifecycle events.
4. Open the new destination to copy its **signing secret** and send a test event.

**Edit or pause:** open a destination → **Edit webhook** to change name, endpoint URL, subscribed events, or delivery status. Turn off **Delivery enabled** to pause attempts without deleting the configuration.

Only org admins and project admins can create or edit destinations; project members can view destinations for projects they can access. Treat the signing secret like a password — store it in a secret manager, never commit or log it.

### Delivery Contract

Delivery is **at least once and not ordered**. The same event can be delivered more than once, and a later lifecycle event can arrive before an earlier one.

Design your receiver to:

- **verify the signature before parsing or processing** the payload;
- **deduplicate by the stable `event_id`**;
- use `source_revision` and `source_ordinal` when ordering events from the same producer matters;
- **durably record accepted work before returning `2xx`**;
- process expensive or failure-prone work asynchronously.

Svix retries failed endpoint attempts. A successful response acknowledges that delivery attempt; it does **not** change the underlying Tensorlake resource.

> **CSRF.** Webhook deliveries are cross-origin `POST`s without a session cookie, so frameworks with CSRF protection enabled by default will reject them (the docs list a `403` from your endpoint as exactly this symptom). Do **not** disable CSRF protection globally — exempt only the webhook route, and rely on Svix signature verification to authenticate the payload.

### Common Envelope

Every lifecycle webhook is a versioned JSON object:

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Stable identifier beginning with `evt_`. **Use it as the deduplication key.** Unchanged across retries. |
| `event_type` | string | One supported lifecycle event name |
| `event_version` | integer | Payload schema version. Current version is `1`. |
| `occurred_at` | string | RFC 3339 UTC time when the transition was recorded |
| `project_id` | string | Public ID of the project that produced the event |
| `source_id` | string | Opaque identifier for the producer ordering domain |
| `source_revision` | string | Unsigned decimal source revision. **Keep it as a string to avoid integer precision loss.** |
| `source_ordinal` | integer | Zero-based order when one source revision produces multiple events |
| `data` | object | Event-specific sandbox, application, or request data |

For related events from the same `source_id`, compare `source_revision` **numerically**, then `source_ordinal`.

### Event Catalog

#### Sandbox events

| Event type | Emitted when |
|---|---|
| `tensorlake.sandbox.created` | A sandbox is persisted for the first time |
| `tensorlake.sandbox.running` | A sandbox enters the running state |
| `tensorlake.sandbox.suspended` | A sandbox enters the suspended state |
| `tensorlake.sandbox.resumed` | A suspended sandbox begins a new generation. Its public status is initially `pending`. |
| `tensorlake.sandbox.terminated` | A sandbox terminates **without** a failure outcome |
| `tensorlake.sandbox.failed` | A sandbox terminates **with** a failure outcome |

`data` contains `previous_status` and a `sandbox` object:

| Sandbox field | Type | Description |
|---|---|---|
| `id` | string | Sandbox ID |
| `name` | string \| null | Name of a named sandbox, when present |
| `type` | string | `named` or `ephemeral` |
| `image` | string \| null | Sandbox image, when present |
| `generation_id` | integer | Sandbox generation, starting at `1` and increasing on resume |
| `status` | string | `pending`, `running`, `suspended`, or `terminated` |
| `outcome` | string \| null | `success`, `failure`, or `null` while no terminal outcome exists |
| `outcome_reason` | string \| null | Allowlisted terminal reason, when available |
| `snapshot_id` | string \| null | Snapshot associated with the sandbox, when present |
| `created_at` | string | RFC 3339 sandbox creation time |
| `resources` | object | Requested CPU, memory, disk, and GPU resources |

```json
{
  "event_id": "evt_019f95fb-7f33-7000-8000-000000000006",
  "event_type": "tensorlake.sandbox.failed",
  "event_version": 1,
  "occurred_at": "2026-07-24T21:15:15.123Z",
  "project_id": "project_123",
  "source_id": "src_01k0example",
  "source_revision": "81247",
  "source_ordinal": 0,
  "data": {
    "previous_status": "running",
    "sandbox": {
      "id": "9q2j1f4n6y8x0r3k5m7pa",
      "name": "build-runner",
      "type": "named",
      "image": "tensorlake/default",
      "generation_id": 2,
      "status": "terminated",
      "outcome": "failure",
      "outcome_reason": "out_of_memory",
      "snapshot_id": null,
      "created_at": "2026-07-24T20:10:00Z",
      "resources": {"cpus": 2, "memory_mb": 4096, "disk_mb": 20480, "gpu_count": 0, "gpu_model": null}
    }
  }
}
```

**Sandbox failure reasons:** `unknown`, `user_terminated`, `timeout`, `internal_error`, `constraint_unsatisfiable`, `executor_removed`, `out_of_memory`, `container_startup_failed`, `pool_deleted`, `container_terminated`, `bad_image`, `image_not_found`, `container_unhealthy`, `function_error`, `function_timeout`, `function_cancelled`, `desired_state_removed`, `process_crash`, `executor_drained`. A **successful** termination can report `unknown`, `user_terminated`, or `timeout`. `outcome_reason` can be `null` when no safe reason is available.

#### Application events

| Event type | Emitted when |
|---|---|
| `tensorlake.application.created` | An application is persisted for the first time |
| `tensorlake.application.updated` | A deployment, metadata, capability, or application state change is persisted |
| `tensorlake.application.deleted` | An existing application is deleted |

`data` contains `previous_version`, `previous_state`, and an `application` object. The `previous_*` fields are `null` for a creation event.

| Application field | Type | Description |
|---|---|---|
| `name` | string | Application name |
| `version` | string | Application version |
| `state` | string | `active` or `disabled` |
| `disabled_reason` | string \| null | Reason the application is disabled, when present |
| `created_at` | string | RFC 3339 application creation time |

#### Application-request events

| Event type | Emitted when |
|---|---|
| `tensorlake.application.request.created` | An application request is created |
| `tensorlake.application.request.completed` | An application request completes successfully |
| `tensorlake.application.request.failed` | An application request reaches a failed terminal state |

`data` contains an `application` identity (`name`, `version`) and a `request` object:

| Request field | Type | Description |
|---|---|---|
| `id` | string | Application request ID |
| `status` | string | `created`, `completed`, or `failed` |
| `failure_reason` | string \| null | Allowlisted reason for a failed request |
| `created_at` | string | RFC 3339 request creation time |
| `finished_at` | string \| null | RFC 3339 terminal time; `null` until the request finishes |

**Application-request failure reasons:** `unknown`, `internal_error`, `function_error`, `function_timeout`, `request_error`, `constraint_unsatisfiable`, `cancelled`, `out_of_memory`.

### Signature Verification

Every delivery is signed by Svix with the destination's signing secret. **Verify before parsing or processing.**

Get the secret: project → **Webhooks** → open the destination → **Signing secret**, a value beginning with **`whsec_`**. Store it in your secret manager.

Svix includes three headers with each delivery: `svix-id`, `svix-timestamp`, `svix-signature`.

Verify the **raw request body** plus the request headers with your signing secret, using an [official Svix library](https://docs.svix.com/receiving/verifying-payloads/how) (recommended) or Svix's [manual verification procedure](https://docs.svix.com/receiving/verifying-payloads/how-manual). **Reject requests with missing or invalid signature headers.** Only after successful verification, parse the payload as the appropriate lifecycle event.

### Testing

Destination page → **Test delivery** → pick one of the destination's subscribed event types → **Test webhook**. Tensorlake sends a signed synthetic payload through the destination's normal Svix signing and delivery path. Confirm your endpoint validates the signature, records the `event_id`, parses the expected event shape, and returns `2xx`.

A test delivery uses a valid example payload; it does **not** create, update, suspend, terminate, or delete a real Tensorlake resource.

| Symptom | Check |
|---|---|
| Signature verification fails | Verify with the **raw** request body, all three Svix headers, and this destination's signing secret |
| Endpoint returns `404` | Confirm the complete URL path — paths are case-sensitive |
| Endpoint returns `403` | Confirm the route accepts server-to-server `POST` and does not require browser session or CSRF credentials |
| Event delivered repeatedly | Return `2xx` after durable acceptance and deduplicate by `event_id` |
| An expected event never arrives | Confirm delivery is enabled and the event type is selected for this project-scoped destination |

## EU Endpoints

Tensorlake APIs are available in the EU region for data residency and compute in Europe.

- **EU HTTP endpoint:** `https://api.eu.tensorlake.ai/`
- **The same API key works in both US and EU regions.**
- **Webhooks are supported in both regions.**

For Orchestration, pin the region on the decorator (per the Applications SDK reference):

```python
@application(region="eu-west-1")   # or "us-east-1"; default is any region
@function()
def my_workflow(data: str) -> str:
    ...
```

`region` can also be set per `@function()`.

> The EU endpoints doc page still shows a legacy Workflows example (`from tensorlake.functions_sdk import Graph`, `Graph(name=..., region=Region.EU)`). That API does not appear anywhere else in the current docs — use `@application(region="eu-west-1")` and treat that snippet as stale.

## Billing

Billing in Tensorlake Cloud is **usage-based**. Current usage and invoices are on the Billing page in the dashboard. See [tensorlake.ai/pricing](https://www.tensorlake.ai/pricing) for plan limits (which also cap sandbox `timeout_secs` — see [sandbox_persistence.md](sandbox_persistence.md#resource-limits-and-timeouts)).

## Security

Data that may be stored on Tensorlake: **files and state inside your sandboxes, snapshots, and the inputs and outputs of your workflows.**

**Storage policies:**

1. **Location** — AWS S3, encrypted at rest and in transit.
2. **Access** — strictly limited to the internal services operating on your behalf, so only authorized and authenticated processes can touch stored data.
3. **Retention** — you can delete your data at any time using the APIs.
4. **Usage** — **your data is never used for training.**

**Deleting data:**

- **Sandbox deletion** permanently removes its files and state; **snapshots you created are retained until you delete them.**
- **Workflow data** — inputs and outputs of workflow runs can be deleted permanently.
- **Immediate deletion** — requested data is removed from active systems immediately.
- **API access** — deletion can be performed through API endpoints, so it can be integrated into workflows and compliance processes.

For complete data deletion requests or audit-log access, contact `support@tensorlake.ai`.

**Encryption:** all data at rest in S3 is encrypted with industry-standard algorithms; all data in transit uses SSL/TLS.

**Compliance:** HIPAA and SOC 2 Type II compliant, EU data residency, zero data retention. Hybrid and fully-disconnected on-prem options exist for data that must never leave your servers — contact `support@tensorlake.ai`.

**Authorized subprocessors:** AWS (cloud infra, US/EU), OpenAI (AI, US/EU), Anthropic (AI, US/EU), Datadog (error monitoring, US), PostHog (product analytics, US), Google Cloud (cloud infra, US/EU), Microsoft Azure (cloud infra, US/EU), Lambda Labs (cloud infra, US/EU).

## Single Sign-On (SSO)

SSO lets your team sign in through your company's identity provider instead of managing separate Tensorlake credentials.

**Prerequisites:** you must be an **organization admin**, and SSO access must be enabled for your organization (request it from the SSO settings page).

**Protocols:** **OIDC** (recommended — Google Workspace, Okta, Auth0) and **SAML 2.0** (Azure AD / Entra ID, OneLogin, other SAML IdPs).

Setup is at **Organization Settings → SSO → Configure SSO Connection**:

| Field | Description |
|---|---|
| **Domain** | Your organization's email domain (e.g. `yourcompany.com`). Users with this domain are directed to your IdP. |
| **Issuer URL** | Issuer or entity ID from your IdP |
| **Client ID** | Application/client ID assigned by your IdP |
| **Client Secret** | Client secret from your IdP (**OIDC only**) |
| **Authorization Endpoint** | URL where users are sent to authenticate (OIDC) |
| **Token Endpoint** | URL used to exchange authorization codes for tokens (OIDC) |
| **ACS URL / SSO URL** | Assertion Consumer Service URL (SAML) — provided by Tensorlake |
| **Certificate** | X.509 signing certificate from your IdP (SAML) |

**Attribute mapping:** your IdP must send at minimum the user's **email address**; first/last name are recommended for a complete profile.

**Test before enforcing.** Click **Test Connection**, authenticate at your IdP, and the provider is marked **Verified**. **SSO enforcement cannot be enabled until a successful test login has completed** — enforcing an untested configuration could lock users out.

**Enforcement (optional).** Requires all organization members to sign in through your IdP; password-based login is disabled for everyone else.

1. Designate **at least one organization admin as a bypass user** — required before enforcement can be enabled.
2. Toggle **Enforce SSO**.

**Bypass users** are org admins who retain password login for emergency recovery (e.g. your IdP goes down and you need to disable enforcement). Only org admins can be bypass users, and only org admins can enable/disable enforcement or manage bypass users.

> **Enabling enforcement invalidates all existing sessions for the organization.** Every member except bypass users is signed out and must re-authenticate through the IdP.
