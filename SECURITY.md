# Security Policy

Downtify is a self-hosted music server: people run it on their home servers and NAS boxes, often reachable from the internet, with their music library, their accounts and sometimes their YouTube cookies on it. We take its security seriously, and we are grateful to everyone who helps keep it safe.

This document explains which versions receive security fixes, how to report a vulnerability, what you can expect from us after you do, what is and isn't in scope, and how to run Downtify safely.

## Table of contents

1. [Supported versions](#supported-versions)
2. [Reporting a vulnerability](#reporting-a-vulnerability)
3. [What to include in a report](#what-to-include-in-a-report)
4. [What happens after you report](#what-happens-after-you-report)
5. [Disclosure policy](#disclosure-policy)
6. [Recognition](#recognition)
7. [Scope](#scope)
8. [Safe harbor](#safe-harbor)
9. [How we keep Downtify secure](#how-we-keep-downtify-secure)
10. [Running Downtify safely](#running-downtify-safely)
11. [Secrets in public reports](#secrets-in-public-reports)

---

## Supported versions

Downtify releases often, and only the **latest release** receives security fixes. A fix is shipped as a new release; older releases are not patched. Please update before reporting, and keep your installation up to date.

| Component | Supported | Where to get it |
| --- | --- | --- |
| Downtify server, web app and Docker image | The latest release | [GitHub Releases](https://github.com/henriquesebastiao/downtify/releases), `ghcr.io/henriquesebastiao/downtify:latest` |
| Downtify for Android | The latest release | [GitHub Releases](https://github.com/henriquesebastiao/downtify-android/releases) (also through Obtainium) |
| Any older release | No | Update to the latest release |

Vulnerabilities in code that is on the `main` branch but not released yet are welcome too: they are fixed before they reach a release.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, pull requests, or social media.** A public report puts every Downtify server at risk before a fix exists.

Report it privately instead, in one of these ways:

1. **GitHub private vulnerability reporting (preferred).** Open a report at <https://github.com/henriquesebastiao/downtify/security/advisories/new>. Only you and the maintainer can see it, we can discuss the fix and credit you there, and it becomes the published security advisory once the fix is released. Use this form for the **Android app** too, and say in the title that it concerns `downtify-android`.
2. **Email.** Write to **[contato@henriquesebastiao.com](mailto:contato@henriquesebastiao.com)** with a subject that starts with `[Security]`. Use this if you can't use GitHub, or if you're not sure whether what you found is a vulnerability.

If you are not sure whether something is a security problem, report it privately anyway: we would rather receive a report that turns out to be harmless than miss one.

## What to include in a report

A good report lets us reproduce the problem quickly. Please include as much of this as you can:

- **What is affected:** the component (server, web app, Docker image, Android app) and the version you tested (**Settings → About** in the web app shows it, or the image tag).
- **How it is set up**, when it matters: Docker or a local install, behind a reverse proxy or not, accounts on or off (`DOWNTIFY_DISABLE_AUTH`), OIDC, SQLite or PostgreSQL.
- **The kind of issue**, for example path traversal, cross-site scripting, authentication bypass, privilege escalation, server-side request forgery.
- **Who can exploit it:** someone with no account, a signed-in user, a paired app, or someone on the same network.
- **Step-by-step instructions to reproduce it**, with a proof of concept (a request, a script, a crafted file or link) where possible.
- **The impact:** what an attacker could read, change or break, and on whose server.
- **A suggested fix**, if you have one (optional).
- Whether the issue is already known to anyone else, and **how you would like to be credited**.

Please test against your own installation, never against someone else's server (see [Safe harbor](#safe-harbor)).

## What happens after you report

Downtify is maintained by one person, so these are commitments made in good faith rather than a service-level agreement. We aim to:

| Step | Target |
| --- | --- |
| Acknowledge your report | Within **3 business days** |
| Initial assessment: confirm (or not) the issue and its severity | Within **7 days** |
| Release a fix for a **critical** issue | Within **7 days** of confirming it |
| Release a fix for a **high** severity issue | Within **30 days** |
| Release a fix for a **medium** or **low** severity issue | Within **90 days** |

Severity follows GitHub's levels (critical, high, medium, low), which are based on [CVSS](https://www.first.org/cvss/). While we work on the issue we keep you informed whenever its status changes, may ask you for more details, and may ask you to check that the fix works. If we conclude that a report is not a vulnerability, or is out of scope, we tell you why.

If you have not heard back within the acknowledgement time, please send a short reminder by email; reports do get lost in spam folders.

## Disclosure policy

We follow **coordinated disclosure**:

1. We fix the issue privately, in a temporary private fork of the security advisory when that helps.
2. We release the fix, then publish a [GitHub Security Advisory](https://github.com/henriquesebastiao/downtify/security/advisories) describing the issue, the affected versions, the fixed version and how to protect yourself, and request a CVE identifier for it when appropriate. The release notes point to the advisory.
3. Please keep the details private until the advisory is published, or until **90 days** after your report, whichever comes first. If a fix needs more time, we will ask you for an extension and explain why.

If a vulnerability is being actively exploited, we may publish a warning with mitigations before a fix is ready.

## Recognition

Downtify does not have a bug bounty program and cannot offer money for reports.

We do credit reporters, if they want to be credited, in the security advisory (as a credited reporter, which GitHub shows on the advisory and in the CVE), and in the release notes of the version that fixes it. Tell us the name or GitHub account you would like to be credited under, or that you prefer to stay anonymous.

## Scope

### In scope

Any vulnerability in the code of this repository or of [`downtify-android`](https://github.com/henriquesebastiao/downtify-android), in their latest release or on their `main` branch, including but not limited to:

- **Authentication:** bypassing sign-in, stealing or forging sessions, device tokens or pairing codes, OpenID Connect flaws, getting around the sign-in and pairing rate limits, or weaknesses in how passwords and tokens are stored.
- **Authorization:** a user reaching what only an admin may do, a paired app doing what [paired apps may not do](https://downtify.henriquesebastiao.com/features/mobile-apps/#what-a-paired-app-may-do), one account reading or changing another account's private data (private playlists, account settings, the activity log, a personal library with **Each user has their own library** on), and cross-site request forgery.
- **Files:** reading, writing or deleting files outside the library and data folders (path traversal, symlinks, crafted `.m3u` playlists, crafted file names or tags), and uploads that do more than they should.
- **Injection:** command or argument injection into `yt-dlp`, `ffmpeg` or other tools, SQL injection, and template or header injection.
- **The web app:** cross-site scripting (including through song tags, lyrics, playlist names or other content that comes from files and third-party services), open redirects, and leaking credentials to other origins.
- **Requests the server makes:** server-side request forgery through links, cover art, artist images, feeds, the proxy settings or integrations (Navidrome, slskd, Deemix).
- **Secrets:** credentials, cookies or tokens exposed in API responses, logs, error messages, backups or exports.
- **The Docker image** built from this repository, and the release pipeline (the GitHub Actions workflows).
- **The Android app:** how it stores its token and offline files, how it validates the server's TLS certificate and handles client certificates, its exported components, intents and deep links, and anything that lets another app or a malicious server compromise the device or the account.

### Out of scope

The following are not considered vulnerabilities in Downtify, or are not handled through this policy:

- **Servers run with accounts off** (`DOWNTIFY_DISABLE_AUTH=true`), where by design whoever reaches the server is its admin, and servers still using the default `admin` / `downtify` password. See [Users & Sign-in](https://downtify.henriquesebastiao.com/features/users/).
- **What an admin can already do.** Admins are fully trusted: they control settings, folders, integrations and every account. An admin attacking their own server, or another admin, is not a vulnerability. Escalating *to* admin is.
- **Hidden songs being reachable by their address.** Hiding songs, albums and artists from users controls what is listed, not who can fetch a file whose address they already know, as [the documentation says](https://downtify.henriquesebastiao.com/features/users/#hiding-from-users).
- **Weaknesses in third-party services or software** that Downtify uses: Spotify, YouTube and YouTube Music, Deezer, SoundCloud, LRCLIB and the other lyrics providers, Navidrome, slskd, Deemix, or libraries and tools such as `yt-dlp`, `ffmpeg` and FastAPI. Please report those to their maintainers. A vulnerability in a dependency *is* in scope when you can show that it is exploitable through Downtify.
- **Denial of service** through sheer volume of traffic, and resource exhaustion that needs a signed-in account to cause (for example, queueing a very large number of downloads).
- **Reports without a demonstrated impact**: missing security headers or cookie attributes, version disclosure, clickjacking on pages with no sensitive action, self-XSS, CSV injection, or the raw output of an automated scanner.
- **Attacks that need** physical access to a device, a rooted or jailbroken phone, an already-compromised server or browser, social engineering of the maintainer or users, or a browser or Android version that no longer receives security updates.
- **Copyright, licensing and terms-of-service questions** about what users download. These are not security issues; see the warning in the [README](README.md#license).
- **The documentation website**, a static site; report mistakes in it as regular issues.

If you are unsure whether something is in scope, report it privately and ask.

## Safe harbor

We consider security research carried out in good faith and in line with this policy to be authorized, we will work with you to understand and fix the issue, and we will not pursue or support legal action against you for it. Good faith means that you:

- test only on installations you own or have explicit permission to test;
- do not access, change, delete or keep other people's data, and stop as soon as you reach data that isn't yours;
- do not degrade the service for others (no denial-of-service testing on servers you don't own);
- do not use social engineering, phishing or physical attacks;
- report the vulnerability privately and promptly, and give us a reasonable time to fix it before disclosing it, as described in the [Disclosure policy](#disclosure-policy).

This safe harbor covers the Downtify project only. It cannot authorize testing of other people's Downtify servers or of third-party services, which have their own rules.

## How we keep Downtify secure

What the project does today:

- **Private reporting and advisories** through GitHub, as described above.
- **Secret scanning with push protection** on this repository, so credentials are not committed by accident.
- **Dependency updates** through Dependabot for the Python dependencies (`yt-dlp` among them), the Docker base image and the GitHub Actions used in CI.
- **Automated tests** on every pull request, and review by the maintainer of every change before it is merged.
- **Credential masking in logs:** Downtify masks the passwords, tokens, cookies and signed-URL secrets it knows about in what it logs.
- **AI-assisted development, human-reviewed:** the maintainer uses AI coding assistants, as the [Code of Conduct](CODE_OF_CONDUCT.md#how-the-maintainer-uses-ai) explains. Security fixes, like every change, are reviewed, tested and released by a person.

## Running Downtify safely

Most incidents with self-hosted software come from how it is exposed, not from a bug. Before you make Downtify reachable from outside your home network:

- **Change the default password.** A new server has the account `admin` / `downtify`, and anyone who knows Downtify knows it. Change it in **Settings → General → Account**. See [Users & Sign-in](https://downtify.henriquesebastiao.com/features/users/#signing-in-for-the-first-time).
- **Keep accounts on.** Never set `DOWNTIFY_DISABLE_AUTH=true` on a server others can reach: with accounts off, anyone who can reach it can change settings, delete music and pair a phone.
- **Use HTTPS.** Put Downtify behind a reverse proxy (Caddy, nginx, Traefik…) with a valid certificate: passwords and the apps' tokens travel with every request. Set `DOWNTIFY_TRUSTED_PROXIES` to your proxy's address so Downtify trusts its forwarded headers, and only its. See [Behind a reverse proxy](https://downtify.henriquesebastiao.com/features/mobile-apps/#behind-a-reverse-proxy).
- **Expose as little as you can.** A VPN such as Tailscale or WireGuard is safer than opening a port to the internet. Single sign-on through [OpenID Connect](https://downtify.henriquesebastiao.com/features/users/#openid-connect), with `DOWNTIFY_DISABLE_LOCAL_LOGIN=true`, lets your identity provider add multi-factor authentication.
- **Give each person their own account**, and admin rights only to people who need them.
- **Review paired apps** in **Settings → Apps** from time to time; **Sign out everywhere** unpairs every app and signs out every browser if a phone is lost.
- **Protect the data folder.** `/data` holds the database, the sessions and the uploaded YouTube cookies. Keep it private, and keep your backups of it private too.
- **Treat YouTube cookies like a password.** They give access to the Google account they come from; preferably export them from a separate account used only for Downtify.
- **Update regularly.** Only the latest release receives security fixes. Watch the repository's releases (**Watch → Custom → Releases** on GitHub) to hear about them.
- **Install the Android app** only from the project's [GitHub Releases](https://github.com/henriquesebastiao/downtify-android/releases) or through Obtainium pointed at that repository.

## Secrets in public reports

Bug reports and discussions are public. Before posting logs, settings or screenshots, remove passwords, session cookies, device tokens, pairing codes, OIDC secrets, YouTube cookies and the address of your server if you don't want it known.

If you posted a secret by mistake, delete or edit the post and **change the secret right away**: sign out everywhere, change the password, or export new cookies. Editing a post does not erase it from its history or from notification emails. You can also ask the maintainer at [contato@henriquesebastiao.com](mailto:contato@henriquesebastiao.com) to remove it for good. If you see someone else's secret, do not use it; let the maintainer know.

---

Thank you for helping keep Downtify and its users safe.
