# AWS Deployment — Design Spec

Date: 2026-06-11
Status: Approved (pending implementation plan)

## 1. Overview

Deploy the Jubilous Telegram bot to AWS as a single always-on EC2 instance,
provisioned with Terraform, with automated redeploys via GitHub Actions on
push to `main`.

## 2. Architecture

```
GitHub repo (poissondemars/Jubilous)
   │ push to main (after tests pass)
   ▼
GitHub Actions ──(OIDC, no static keys)──► AWS IAM Role
   │
   ▼
AWS SSM Send-Command ──► EC2 instance (t3.micro, us-east-1)
                              │
                              ├─ git pull + systemctl restart jubilous
                              ├─ jubilous.service (systemd) runs bot.py
                              ├─ jubilous.db (SQLite, local disk)
                              └─ .env populated from SSM Parameter Store (BOT_TOKEN)
```

- No public ingress: the security group has zero inbound rules. The bot only
  makes outbound calls to the Telegram API (long polling). GitHub Actions
  reaches the instance via AWS SSM (AWS API), not SSH.
- SQLite stays on the instance's EBS root volume — matches the current
  single-file design with no code changes. If the instance is replaced,
  `jubilous.db` is lost. This is an accepted limitation for this project (no
  RDS/EFS, no automated backups).

## 3. Terraform layout (`terraform/`)

```
terraform/
├── versions.tf      # provider/version pins (aws, required_version)
├── variables.tf     # region (us-east-1), instance_type (t3.micro),
│                     # github_repo, repo_clone_url
├── main.tf          # provider config
├── network.tf       # security group (no inbound, all outbound) in default VPC
├── ec2.tf           # EC2 instance, IAM instance role/profile, user_data
├── ssm.tf           # SSM SecureString parameter "/jubilous/bot_token"
├── github_oidc.tf   # GitHub OIDC provider + deploy IAM role/policy
├── outputs.tf       # instance_id, instance_role_arn, deploy_role_arn
└── user_data.sh.tpl # bootstrap script (templated with repo clone URL)
```

State is local (`terraform.tfstate*`, gitignored) — appropriate for a
single-operator project.

## 4. EC2 bootstrap (`user_data.sh.tpl`)

Runs once at first boot (Amazon Linux 2023, which preinstalls the SSM agent
and `python3`/`git`):

1. Install `python3`, `python3-venv`/`pip`, `git` if not already present.
2. `git clone <repo_clone_url> /opt/jubilous`
3. `python3 -m venv /opt/jubilous/.venv && /opt/jubilous/.venv/bin/pip install -r /opt/jubilous/requirements.txt`
4. Fetch `BOT_TOKEN` from SSM Parameter Store
   (`aws ssm get-parameter --name /jubilous/bot_token --with-decryption`)
   and write `/opt/jubilous/.env`:
   ```
   BOT_TOKEN=<fetched value>
   DB_PATH=/opt/jubilous/jubilous.db
   ```
5. Install a systemd unit `jubilous.service`:
   - `WorkingDirectory=/opt/jubilous`
   - `ExecStart=/opt/jubilous/.venv/bin/python bot.py`
   - `Restart=always`
   - `User=ec2-user`
   Then `systemctl enable --now jubilous`.

## 5. IAM and secrets

- **EC2 instance role**: managed policy `AmazonSSMManagedInstanceCore`
  (enables SSM Session Manager + Run Command on the instance), plus an
  inline policy granting `ssm:GetParameter` on
  `arn:aws:ssm:us-east-1:*:parameter/jubilous/bot_token` only.
- **SSM parameter** `/jubilous/bot_token` (type `SecureString`): created by
  Terraform with a placeholder value and
  `lifecycle { ignore_changes = [value] }`, so the real token is never
  stored in Terraform state or shown in diffs. After `terraform apply`, the
  real value is set once via:
  ```bash
  aws ssm put-parameter --name /jubilous/bot_token --type SecureString \
    --value "<real-bot-token>" --overwrite
  ```
  This manual step is documented in the plan and README.
- **GitHub OIDC provider** (`token.actions.githubusercontent.com`) + a
  deploy IAM role. Trust policy restricts the role to
  `sub: repo:poissondemars/Jubilous:ref:refs/heads/main`. The role's policy
  grants:
  - `ssm:SendCommand` for document `AWS-RunShellScript`, scoped to the
    instance's ARN
  - `ssm:GetCommandInvocation` (needed to poll command status), scoped to
    the instance's ARN

## 6. CI/CD (`.github/workflows/deploy.yml`)

Triggered on push to `main`:

1. Checkout, set up Python, run `pytest` (existing test suite). Deploy steps
   only run if tests pass.
2. `aws-actions/configure-aws-credentials` using
   `role-to-assume: <deploy_role_arn>` (OIDC — no stored AWS keys in GitHub).
3. `aws ssm send-command` with document `AWS-RunShellScript`, targeting the
   instance ID (stored as a GitHub Actions repository variable, taken from
   the Terraform `instance_id` output), running:
   ```bash
   cd /opt/jubilous && sudo -u ec2-user git pull && sudo systemctl restart jubilous
   ```
4. Poll `aws ssm get-command-invocation` until the command completes; fail
   the job if the remote command's status is not `Success`.

## 7. Operational notes (documented in README)

- **Logs**: `aws ssm start-session --target <instance_id>`, then
  `journalctl -u jubilous -f`.
- **First-time setup**:
  1. `terraform init && terraform apply` (in `terraform/`)
  2. Set the real bot token: `aws ssm put-parameter --name /jubilous/bot_token --type SecureString --value "<token>" --overwrite`
  3. Set the GitHub Actions repository variable `EC2_INSTANCE_ID` to the
     Terraform `instance_id` output, and `AWS_DEPLOY_ROLE_ARN` to the
     `deploy_role_arn` output.
  4. Push to `main` (or manually trigger the workflow) to perform the first
     deploy.
- **Redeploy**: automatic on push to `main` via the GitHub Actions workflow.
- **Teardown**: `terraform destroy` — this deletes the instance and
  `jubilous.db` with it. Back up the database first if needed (e.g.
  `aws ssm start-session` + `scp`-equivalent via S3 upload, or accept data
  loss for a course project).
- **Limitations** (carried over / added to README):
  - Single EC2 instance, single SQLite file — no horizontal scaling, no
    automated backups.
  - Replacing the instance (e.g. via `terraform apply` changes that force
    recreation) loses `jubilous.db`.
  - Reminder timing limitations from the application design spec
    (hourly-poll jitter, etc.) are unchanged by this deployment.

## 8. Out of scope

- Multi-instance / load-balanced deployments
- RDS or other managed database migration
- Automated database backups/snapshots
- Monitoring/alerting (CloudWatch alarms, etc.)
- HTTPS/webhook-based Telegram integration (bot continues to use long
  polling)
