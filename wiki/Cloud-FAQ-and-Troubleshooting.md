# FAQ & Troubleshooting

Quick answers to common questions, then fixes for the situations you are most
likely to hit. Each answer links to the page with the full story.

## FAQ

### Account & access

**How do I get an API key or use my own editor?**
Create a personal token under **Profile → API keys**, or clone the repo over HTTPS
or SSH. See [[Account & Security|Cloud-Account-and-Security]] and
[[Repository & Editing|Cloud-Repository-and-Editing]].

### Organizations & team

**What's the difference between a personal and a cooperative organization?**
Personal is solo; cooperative lets you invite teammates with roles. You can convert
personal → cooperative any time. See
[[Organizations & Team|Cloud-Organizations-and-Team]].

**Who can invite people, and who pays?**
In a cooperative organization, the **owner** or an **admin** invites members.
Billing is per organization and only the **owner** changes the plan.

### Projects & deployment

**Should I start blank or from the example?**
Start from the **example study** for your first project — it comes with sample data
so every screen works immediately. See [[Your First Project|Cloud-Your-First-Project]].

**Where is my survey's public link?**
On the **Deployments** card once the deployment is **Live**. Respondents need no
account. See [[Deploying a Survey|Cloud-Deploying-a-Survey]].

**What's the difference between Preview and Deploy?**
**Preview** builds a staging version that does **not** collect data; **Deploy**
publishes a live survey that does.

### Data

**How do I get my data out?**
**Database → Export** to CSV, Excel, SPSS (`.sav`), Parquet, or SQLite. See
[[Viewing & Exporting Data|Cloud-Viewing-and-Exporting-Data]].

**Can I delete a single response?**
Yes — **Database → Delete** on the row (useful for GDPR erasure). The action is
logged in **Activity**.

### Plans

**What does Free include, and what's gated?**
Free gives 2 projects, 2 members, and 500 responses per project. Webhooks and
schedules need **Plus**; connectors, Git mirrors, and SSO need **Pro**; self-hosted
is **Corporate**. See [[Plans & Billing|Cloud-Subscription-Tiers]].

**If I downgrade, do I lose anything?**
No. Your projects and members keep working — you just can't exceed Free's caps or
use paid features afterward.

## Troubleshooting

### "Upgrade required" / a button is disabled

You reached a plan limit (for example a third project on Free) or used a feature
your plan doesn't include. Stay within your plan's caps, or open
**Organization settings → Billing** to upgrade. See
[[Plans & Billing|Cloud-Subscription-Tiers]].

### A commit failed validation

The file shows an error or warning count instead of the green **valid** badge.
Click the badge to read what's wrong, fix it, and commit again — nothing goes live
until it passes. See [[Validation and Linting|Validation-and-Linting]].

### A deployment failed or is stuck

Open the build **Logs** on the deployment card to see what failed, fix it in the
repo, then **Redeploy**. A build also can't start while another is in progress for
the same environment — wait for it to finish.

### An analysis run failed

Open the run and read its **Logs**. If a step depends on an earlier one (for
example, tables need cleaned and weighted data first), run the earlier step — or use
**Run all** to run every step in order. See
[[Analysis & Reports|Cloud-Analysis-and-Reporting]].

### I can't invite someone

Check all of these: the organization is **cooperative**, you are the **owner** or an
**admin**, the person already has a siamang Cloud account, and your plan has member
room. See [[Organizations & Team|Cloud-Organizations-and-Team]].

### Clone or push fails

For **SSH**, add your public key under **Profile → SSH keys** first. If a token
stopped working, re-copy the command from **Repository → Connect locally**. See
[[Account & Security|Cloud-Account-and-Security]].

### Connectors aren't moving data

Connectors are marked **Coming soon** and don't transfer data yet. Use
**Database → Export** to get your data out in the meantime.

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] · [[Using the Web App|Cloud-Web-App]] · [[Plans & Billing|Cloud-Subscription-Tiers]] · [[siamang Cloud — Overview|Cloud-Overview]]
