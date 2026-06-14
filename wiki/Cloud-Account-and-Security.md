# Account & Security

This page covers your **personal account** — your name, password, theme, and the
keys that let outside tools and your own machine work with the platform. These
settings are yours and follow you across every organization you belong to.

Open them from the **account menu** in the top bar → **Profile**. Profile has five
tabs: **Account**, **Security**, **Appearance**, **API keys**, and **SSH keys**.

## Your profile

The **Account** tab holds your **display name** — the name teammates see next to
your activity. Edit it and save.

## Change your password

**What you'll need:** your current password.

**Steps**
1. Open the **account menu** (top bar) → **Profile**.
2. Go to the **Security** tab.
3. Enter your **current password**, then your **new password** twice.
4. Click **Save**.

**Result:** your password is updated; you stay signed in.

## Appearance

The **Appearance** tab switches between **light** and **dark** theme. It is the
same toggle as the one in the top bar — set it whichever way you prefer.

## API keys

An **API key** is a personal token (it looks like `sck_…`) that lets scripts,
command-line tools, or your own programs talk to siamang Cloud as you, without a
password. Use one when you want to automate something against the API.

**What you'll need:** none — any signed-in user can create a key.

**Steps**
1. Open **Profile → API keys**.
2. Click **New key**, give it a **name** you will recognize later, and create it.
3. **Copy the token now.** It is shown **once**; after you close the dialog only
   its name and a hash remain.
4. Use it in a request header: `Authorization: Bearer sck_…`.

**Result:** the key appears in your list. Revoke it any time with **Revoke**, which
immediately stops it from working.

> Treat a key like a password. If one leaks, revoke it and create a new one.

## SSH keys

Add an **SSH key** when you want to **clone and push** a project's repository from
your own machine over SSH (instead of editing in the browser). You add your
**public** key; the private half never leaves your computer.

**What you'll need:** an SSH key pair on your machine (`ssh-keygen` creates one).

**Steps**
1. Copy your **public** key (for example the contents of `~/.ssh/id_ed25519.pub`).
2. Open **Profile → SSH keys**.
3. Click **Add SSH key**, paste the public key, give it a label, and save.
4. Now clone or push using the SSH address shown under **Repository →
   Connect locally**.

**Result:** Git operations over SSH are authorized as you. See
[[Repository & Editing|Cloud-Repository-and-Editing]] for the clone/push steps.

## See also

[[Organizations & Team|Cloud-Organizations-and-Team]] · [[Repository & Editing|Cloud-Repository-and-Editing]] · [[Using the Web App|Cloud-Web-App]] · [[Plans & Billing|Cloud-Subscription-Tiers]]
