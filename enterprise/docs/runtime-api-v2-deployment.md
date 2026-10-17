# Runtime API V2 — Deployment & Configuration

Per-user, SaaS-only opt-in that routes a conversation's sandbox lifecycle through
**Runtime API V2** (warm pools) instead of V1. V1 remains the default and is
unchanged; V2 is enabled per user via a new **Settings → Sandbox** tab.

**Image (POC):** `ghcr.io/openhands/enterprise-server:sha-a39a510`
(branch `jl/runtime-v2-saas-opt-in`)

## 0. Do this first — apply the DB migration

The enterprise image does **not** run migrations on startup (its CMD is just
`uvicorn saas_server:app`). Apply the enterprise alembic head — revision **118**
(`117 → 118`) — to the SaaS DB **before/with** rolling out the image, via your
normal migration mechanism (init container / migration job). Equivalent of:

```bash
# from the enterprise/ working dir in the image (poetry env)
alembic upgrade head        # applies 118_add_runtime_v2_opt_in
```

Migration 118 adds (all additive / backward-compatible):

- `user.use_runtime_v2` — bool, server default `false`
- `user.warm_runtime_config` — string, nullable
- `v1_remote_sandbox.sandbox_template` — string, nullable

If the image is deployed without 118, settings load will query columns that do
not exist and error. V1 keeps working with these columns present and unused.

> OSS-only note: the OSS `app_server` carries an equivalent migration `011` that
> auto-applies at startup and adds the same `sandbox_template` column. OSS and
> enterprise use separate DBs/trees, so there is no double-apply — ignore `011`
> for the SaaS deploy.

## 1. Environment variables

Read only when `RUNTIME=remote` (the SaaS default), in the same process as the
existing V1 vars. Set them on the **enterprise-server** deployment.

| Variable | Required? | Default / fallback | Purpose |
|---|---|---|---|
| `SANDBOX_WARM_RUNTIME_CONFIGS` | **Yes, to enable the feature** | unset/empty/invalid ⇒ feature **off** (Sandbox tab hidden, everyone on V1) | JSON object mapping warm-pool / `sandbox_template` name → user-facing display name. Populates the SaaS "Sandbox" tab dropdown and validates a user's saved selection. |
| `SANDBOX_REMOTE_RUNTIME_API_URL_V2` | No | falls back to `SANDBOX_REMOTE_RUNTIME_API_URL` (V1) | Base URL of the V2 runtime-api. Set this if V2 is a separate endpoint from V1. |
| `SANDBOX_API_KEY_V2` | No | falls back to `SANDBOX_API_KEY` (V1) | `X-API-Key` for the V2 runtime-api. Set if V2 uses a different key. |

Existing **required** V1 vars (already in your deploy, unchanged):
`SANDBOX_REMOTE_RUNTIME_API_URL`, `SANDBOX_API_KEY`.

## 2. `SANDBOX_WARM_RUNTIME_CONFIGS` format

A JSON **object**, string → string. Keys = warm-pool names that **must exist as
SandboxWarmPools in the V2 runtime-api deployment**. Values = display names.
**Key order is preserved** and drives dropdown order. Invalid JSON or wrong shape
(array, non-string values) is logged and treated as empty (feature off) — it does
**not** crash the app.

```bash
SANDBOX_WARM_RUNTIME_CONFIGS='{"python-gvisor":"Python (gVisor)","node-sysbox":"Node.js (Sysbox)"}'
```

## 3. Cross-system dependency (provision order)

The JSON keys must correspond to real `SandboxWarmPool` resources in the
**separate `runtime-api` V2 service**. Provision/verify those warm pools on the
V2 side **before** referencing them here. If a user's selected pool name is
absent from this map at conversation-start, the backend logs a warning and
silently falls back to V1.

## 4. Enabling end-to-end

1. `RUNTIME=remote` (SaaS default) ✓
2. V2 warm pools provisioned in runtime-api ✓
3. `SANDBOX_WARM_RUNTIME_CONFIGS` set (+ V2 URL/key if separate) ✓
4. **Per-user opt-in:** each user toggles "Use Runtime V2" and picks a config in
   the new **Settings → Sandbox** tab. Default for everyone is V1.

## 5. Verify

- A SaaS user sees a **Sandbox** tab in Settings (only when `warm_runtime_configs`
  is non-empty + SaaS mode).
- The dropdown lists your display names in declared order.
- After a user opts in, new conversations route their sandbox to the V2 endpoint
  (`sandbox_template` set on the `v1_remote_sandbox` row; `session_api_key`
  arrives via the status poll, not at `/start`).

## 6. Rollback

Unset `SANDBOX_WARM_RUNTIME_CONFIGS` (or set `{}`). The tab hides, saved
selections fail validation, and **all new conversations go V1**. In-flight V2
sandboxes keep routing to V2 until torn down. No migration rollback needed
(columns are inert when unused).
