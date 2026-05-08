# Data Model Draft

## users

- `id`
- `email`
- `username`
- `password_hash`
- `display_name`
- `status`
- `created_at`
- `updated_at`

## oauth_clients

- `id`
- `name`
- `secret_hash`
- `redirect_uris`
- `allowed_scopes`
- `created_at`
- `updated_at`

## oauth_authorization_codes

- `code_hash`
- `client_id`
- `user_id`
- `redirect_uri`
- `scope`
- `expires_at`
- `created_at`

## oauth_tokens

- `token_hash`
- `refresh_token_hash`
- `client_id`
- `user_id`
- `scope`
- `expires_at`
- `revoked_at`
- `created_at`

## project_grants

- `user_id`
- `project_id`
- `grant`
- `created_at`

## usage_events

- `id`
- `user_id`
- `project_id`
- `operation`
- `provider`
- `model`
- `input_units`
- `output_units`
- `estimated_cost`
- `metadata_json`
- `created_at`

## audit_events

- `id`
- `actor_user_id`
- `target_user_id`
- `action`
- `metadata_json`
- `ip_address`
- `user_agent`
- `created_at`
