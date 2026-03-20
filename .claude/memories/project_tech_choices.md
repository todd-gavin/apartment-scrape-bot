---
name: Apartment bot tech choices
description: Key technology decisions for the apartment scrape bot — Resend for email, GitHub Actions for scheduling
type: project
---

Email notifications use Resend (not Gmail SMTP or SendGrid). **Why:** Todd chose Resend for its modern API and free tier. **How to apply:** Use `resend` Python SDK, API key stored as GitHub Actions secret.

Scheduling via GitHub Actions cron (not local cron/launchd). **Why:** Todd's laptop may be asleep at scheduled times; cloud-based is more reliable. **How to apply:** `.github/workflows/scrape.yml` handles the 5x daily schedule. DB and session log are committed back to the repo for persistence.
