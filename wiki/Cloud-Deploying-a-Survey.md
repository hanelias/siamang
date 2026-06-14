# Deploying a Survey

Deploying compiles your latest commit and publishes the survey to a **live, public
URL** that respondents open in any browser — no account needed for them. This page
covers previewing, deploying, sharing the link, and watching responses come in.

All of this is on the **Deployments** screen.

## Environments

You deploy into an **environment** — a named, isolated run of the survey. Most
projects use a small **pilot** first, then the **main** run. Each environment has
its own **response cap**, set in `siamang.yaml` (the example study ships with
`pilot` capped at 50 and `main` at 1200). See
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]].

## Preview before you deploy

A **preview** builds a staging version you can click through yourself. It **does
not accept real responses**, so it is the safe way to check the survey first.

**Steps**
1. Open **Deployments**.
2. Click **Preview** (top right).
3. Open the preview link and walk through the survey.

**Result:** you see exactly what respondents will see, with nothing written to your
data.

## Deploy

**What you'll need:** the **member** role or higher, and a commit that passes
validation.

**Steps**
1. On **Deployments**, click **New deployment**.
2. Pick an **environment** (e.g. **pilot**).
3. Confirm to build and publish your latest commit.
4. Watch the build **Logs** stream; the status moves to **Live**.

**Result:** the deployment card shows a **public survey URL**. Status is one of
**Live**, **Building**, **Failed**, or **Stopped**.

## Share the link

Copy the **public survey URL** from the card and send it to respondents — by email,
a panel, a QR code, anywhere. They open it in a browser and submit; they never sign
in.

## Monitor fieldwork

While a survey is **Live**, its card is a live monitor:

- **responses so far**, and against the environment's **cap**, with a progress bar;
- **quota** cells and how full each is (see [[Quotas]]);
- the survey's **codebook** — the variables and their response codes.

Responses also show up in the **Database** and on the **Dashboard** as they arrive
— see [[Viewing & Exporting Data|Cloud-Viewing-and-Exporting-Data]].

## Stop or redeploy

- **Stop** a live survey to stop accepting responses (the collected data stays).
- **Redeploy** a stopped or failed one to build and publish it again.

Both are buttons on the deployment card.

## How many responses you can collect

The effective limit is the **smaller** of two numbers: your **plan's** response cap
and the **environment's** cap in `siamang.yaml`. For example, on **Free** (500 per
project) a `main` environment set to 1200 still stops at 500. Raise the plan cap by
upgrading — see [[Plans & Billing|Cloud-Subscription-Tiers]].

## See also

[[Viewing & Exporting Data|Cloud-Viewing-and-Exporting-Data]] · [[Repository & Editing|Cloud-Repository-and-Editing]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Plans & Billing|Cloud-Subscription-Tiers]]
