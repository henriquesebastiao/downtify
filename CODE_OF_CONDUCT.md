# Code of Conduct

Downtify is a self-hosted music server and an Android app, built in the open by a small community: people who report bugs, suggest features, translate the app and its documentation, review changes and send code. This Code of Conduct describes how we treat each other while doing that, what is not acceptable, and what happens when someone crosses the line.

It is based on the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1, with sections added for things specific to Downtify: the maintainer's commitments, the use of AI tools, secrets and personal data, and the legal side of a music downloader.

## Table of contents

1. [Our pledge](#our-pledge)
2. [Our standards](#our-standards)
3. [Project-specific expectations](#project-specific-expectations)
4. [Use of AI tools](#use-of-ai-tools)
5. [Our commitments as maintainers](#our-commitments-as-maintainers)
6. [Scope](#scope)
7. [Reporting a concern](#reporting-a-concern)
8. [Enforcement guidelines](#enforcement-guidelines)
9. [Appeals](#appeals)
10. [Attribution](#attribution)

---

## Our pledge

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, color, religion, or sexual identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming, diverse, inclusive, and healthy community.

Downtify is translated into many languages and used all over the world. Many people here write in a language that is not their first one. We pledge to read each other generously.

## Our standards

Examples of behavior that contributes to a positive environment for our community include:

- Demonstrating empathy and kindness toward other people
- Being respectful of differing opinions, viewpoints, and experiences
- Giving and gracefully accepting constructive feedback
- Accepting responsibility and apologizing to those affected by our mistakes, and learning from the experience
- Focusing on what is best not just for us as individuals, but for the overall community
- Reviewing the code, not the person: comments on a pull request are about the change, never about whoever wrote it
- Helping newcomers find their way, whether that is their first issue, their first pull request or their first translation
- Searching existing issues and discussions before opening a new one, and adding new information to an existing thread instead of starting a duplicate

Examples of unacceptable behavior include:

- The use of sexualized language or imagery, and sexual attention or advances of any kind
- Trolling, insulting or derogatory comments, and personal or political attacks
- Public or private harassment, including unwelcome direct messages and repeatedly mentioning someone who has asked you to stop
- Publishing others' private information, such as a physical or email address, a home server's address, or account details, without their explicit permission
- Discriminatory jokes and language, in any language, including in code, comments, commit messages, test fixtures, translations and screenshots
- Threats of violence, or encouraging anyone to harm themselves or others
- Deliberately misleading others, for example by impersonating the maintainer or another contributor, or by posting fake bug reports or fake reviews
- Spamming: mass-produced issues, pull requests or comments, advertising, and link farming
- Other conduct which could reasonably be considered inappropriate in a professional setting

## Project-specific expectations

These are not extra rules on top of the ones above; they are what those rules mean in the places Downtify most often runs into trouble.

### Respect the maintainer's and contributors' time

Downtify is maintained by one person in their free time, with help from volunteers. Nobody is owed a fix, a feature or a reply by a given date.

- Be patient. Do not "bump" issues or pull requests repeatedly, mention people only to ask for an update, or demand a release date.
- Ask for support in [GitHub Discussions](https://github.com/henriquesebastiao/downtify/discussions) or with the issue templates, not by private message or email to individual contributors.
- When a feature is declined or an issue is closed, you are welcome to disagree once, with arguments, in the same thread. Re-opening the same request under a new title, or arguing the same point after a decision has been explained, is not.
- Some directions are settled and will not change, for example Downtify will not use Spotify Premium or Spotify Web API credentials. These are explained in [CONTRIBUTING.md](CONTRIBUTING.md) and the issue templates.

### Keep secrets and personal data out of public spaces

Bug reports often need logs, settings and screenshots, and those can carry secrets.

- **Never post** YouTube or Google `cookies.txt` files, session cookies, passwords, device tokens, pairing codes, OIDC client secrets, Navidrome or slskd credentials, API keys, or Proof-of-Origin tokens, not even "just for a minute".
- Review logs before pasting them. Downtify masks the credentials it knows about in its own logs, but it cannot know about everything that passes through a reverse proxy, a Docker setup or another tool.
- Do not post the address of someone else's server, or anything that identifies another person, without their consent.
- If you see someone else's secret posted by mistake, do not use it; tell the maintainer (see [Reporting a concern](#reporting-a-concern)) so it can be hidden, and suggest to its owner that they change it.
- Security vulnerabilities are reported privately, never in public issues or discussions. See [SECURITY.md](SECURITY.md).

### Keep it legal

Downtify is a tool for your own music library. As the [README](README.md#license) says, users are responsible for what they download, and the project does not support unauthorized downloading of copyrighted material. In project spaces:

- Do not share copyrighted audio files, links to pirated content, or other people's account credentials.
- Do not ask for, or offer, help with circumventing DRM, paywalls or access controls of a service, or with breaking the law where you live.
- A bug report may include a public Spotify, Deezer or YouTube link that triggers the bug; the project only uses public endpoints, so the link itself is not sensitive.

### Contributions are licensed

By contributing you agree that your contribution is licensed under the project's [AGPL-3.0](LICENSE) license, and you confirm that you have the right to submit it under that license. Do not submit code, text, images or translations copied from places whose license does not allow it.

## Use of AI tools

AI tools (code assistants, chat assistants, machine translation and the like) are welcome in Downtify, for code, documentation, translations, issues and reviews, under three conditions: **you disclose substantial use, you stay accountable for everything you submit, and the result meets the same bar as any other contribution.**

### Disclose substantial use

Using an AI tool for autocompletion, spelling or grammar does not need to be mentioned. Anything more does. If an AI tool wrote or substantially shaped any of the following, say so:

- code, tests or configuration in a pull request;
- a pull request description, an issue, a discussion post or a review comment;
- documentation or translations;
- an analysis you are sharing, such as a root-cause explanation or a benchmark.

One line is enough, in the pull request description or the post itself, for example: *"AI assistance: Claude Code drafted the parser and the tests; I reviewed and edited them and ran the suite locally."* A commit trailer such as `Co-Authored-By:` or `Assisted-by:` naming the tool is also fine. Disclosure is not a mark against a contribution; it tells reviewers where to look harder.

### Stay accountable

The human who submits a contribution is its author, whatever tools were involved. That means:

- **Understand it.** You must be able to explain every change you submit and answer review questions about it in your own words. "The AI wrote it" is not an answer to a review question.
- **Verify it.** Run the formatter, linters and tests, and do the manual checks [CONTRIBUTING.md](CONTRIBUTING.md#pull-requests) asks for. AI tools confidently invent APIs, options, endpoints, file paths and test results; check them against the code.
- **Keep it focused.** Do not submit large, sweeping or speculative changes because a tool made them easy to produce. Smaller pull requests that someone can actually review are better.
- **Check the facts.** Issues, documentation and reports must describe what really happens in Downtify, not what a tool guessed. Reproduce a bug before reporting it.
- **Respect licenses.** You are responsible for making sure AI output you submit does not reproduce code or text you have no right to contribute under the AGPL-3.0.
- **Respect privacy.** Do not paste other people's personal data, private messages, or details of an undisclosed vulnerability into an AI service.
- **Mind the translations.** Machine or AI translations are a fine starting point, but someone who reads the language should review them before they are submitted, and the pull request should say they were machine-assisted.

### What happens to contributions that don't

Contributions that look like unreviewed AI output (they don't match the code they claim to change, invent features, can't be explained by their author, or ignore the review) may be closed without a detailed review. Repeatedly submitting such content, or hiding substantial AI use when asked about it, is handled under the [Enforcement guidelines](#enforcement-guidelines), like any other conduct that wastes the community's time.

### How the maintainer uses AI

In the same spirit of transparency: the maintainer uses AI coding assistants to develop Downtify, and the repository includes [CLAUDE.md](CLAUDE.md), the project guide those assistants follow. Every change, whoever or whatever drafted it, is reviewed, tested and released by a person, who is accountable for it. Decisions under this Code of Conduct are always made by a person, not by an AI tool.

## Our commitments as maintainers

Asking a lot of contributors comes with obligations. The maintainers of Downtify commit to:

- **Respond.** Read issues, discussions and pull requests, and reply as time allows. When something cannot be done, say so instead of leaving it open forever.
- **Explain decisions.** When a feature is declined, a pull request is closed or a moderation action is taken, give the reason, unless explaining would expose someone who reported a problem.
- **Credit contributions.** Contributors are credited in the commit history, the release notes and, for security reports, the security advisory, unless they prefer otherwise.
- **Apply this Code to ourselves.** The maintainers are held to the same standards as everyone else.
- **Handle reports fairly and confidentially.** Every report is reviewed and investigated promptly, the privacy of the reporter is respected, and no one is retaliated against for reporting a concern in good faith.
- **Step aside when involved.** A maintainer who is the subject of a report, or has a conflict of interest, does not decide on it.
- **Keep the project's spaces safe**, including from spam, scams and malicious links.

### Enforcement responsibilities

Community leaders are responsible for clarifying and enforcing our standards of acceptable behavior and will take appropriate and fair corrective action in response to any behavior that they deem inappropriate, threatening, offensive, or harmful.

Community leaders have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned to this Code of Conduct, and will communicate reasons for moderation decisions when appropriate. On GitHub that includes hiding or editing comments, locking or closing threads, converting issues to discussions, closing pull requests, and blocking accounts from the organization's repositories.

Today the community leader of Downtify is its maintainer, [Henrique Sebastião](https://github.com/henriquesebastiao).

## Scope

This Code of Conduct applies within all community spaces of the Downtify project:

- the [`downtify`](https://github.com/henriquesebastiao/downtify) and [`downtify-android`](https://github.com/henriquesebastiao/downtify-android) repositories on GitHub, including issues, pull requests, code review, discussions, commit messages, release notes, and the content of the code, documentation and translations themselves;
- the documentation website, [downtify.henriquesebastiao.com](https://downtify.henriquesebastiao.com);
- any other space the project creates later, such as a chat server or a forum.

It also applies when an individual is officially representing the community in public spaces, for example when posting from an official project account, or acting as an appointed representative at an online or offline event. Behavior outside these spaces may be taken into account when it targets members of this community or makes the project's spaces unsafe for them.

## Reporting a concern

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the community leaders responsible for enforcement by email at **[contato@henriquesebastiao.com](mailto:contato@henriquesebastiao.com)**. Please use a subject that starts with `[Conduct]`.

It helps to include:

- what happened, and where (links to the comments, issues or pull requests);
- when it happened;
- who was involved, including any witnesses;
- anything else you think is relevant, such as screenshots of content that has since been edited or deleted.

You do not need to have all of this to report, and you do not need to be the person targeted. You will receive an acknowledgement, usually within a few days, and you will be told what was decided when the review is done. Your identity is not shared with the person you reported without your permission.

All community leaders are obligated to respect the privacy and security of the reporter of any incident.

**If your report is about the maintainer**, who today is the only person receiving these emails, you can report it to GitHub instead, through the **Report content** option on the comment or the [GitHub abuse reporting form](https://support.github.com/contact/report-abuse). GitHub's [Community Guidelines](https://docs.github.com/site-policy/github-terms/github-community-guidelines) apply to every repository on the platform.

If you or someone else is in immediate danger, contact your local emergency services first.

**Security vulnerabilities are not conduct reports.** Report them privately as described in [SECURITY.md](SECURITY.md).

## Enforcement guidelines

Community leaders will follow these Community Impact Guidelines in determining the consequences for any action they deem in violation of this Code of Conduct:

### 1. Correction

**Community Impact**: Use of inappropriate language or other behavior deemed unprofessional or unwelcome in the community. This includes a first instance of undisclosed substantial AI use, or of a low-effort contribution that ignores the guidelines above.

**Consequence**: A private, written warning from community leaders, providing clarity around the nature of the violation and an explanation of why the behavior was inappropriate. A public apology may be requested. The content in question may be hidden, edited or closed.

### 2. Warning

**Community Impact**: A violation through a single incident or series of actions.

**Consequence**: A warning with consequences for continued behavior. No interaction with the people involved, including unsolicited interaction with those enforcing the Code of Conduct, for a specified period of time. This includes avoiding interactions in community spaces as well as external channels like social media. Violating these terms may lead to a temporary or permanent ban.

### 3. Temporary ban

**Community Impact**: A serious violation of community standards, including sustained inappropriate behavior, or repeatedly submitting spam or unreviewed AI-generated content after a warning.

**Consequence**: A temporary ban from any sort of interaction or public communication with the community for a specified period of time. No public or private interaction with the people involved, including unsolicited interaction with those enforcing the Code of Conduct, is allowed during this period. Violating these terms may lead to a permanent ban.

### 4. Permanent ban

**Community Impact**: Demonstrating a pattern of violation of community standards, including sustained inappropriate behavior, harassment of an individual, or aggression toward or disparagement of classes of individuals. Also: publishing someone's secrets or personal data on purpose, or using the project's spaces to distribute malware or pirated content.

**Consequence**: A permanent ban from any sort of public interaction within the community.

The steps are guidelines, not a staircase that must be climbed in order: a severe first incident can lead directly to a ban. Clear spam, scams and malicious links are removed and their authors blocked without warning.

## Appeals

If you believe an enforcement decision about you was wrong, you can ask for it to be reviewed by writing to [contato@henriquesebastiao.com](mailto:contato@henriquesebastiao.com) with the subject `[Conduct appeal]`, within 30 days of the decision. Explain what you think was misunderstood or what has changed. Appeals are reviewed by someone other than the person who made the original decision whenever the project has someone who can do so, and the outcome is final.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1, available at <https://www.contributor-covenant.org/version/2/1/code_of_conduct.html>, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Downtify added the sections [Project-specific expectations](#project-specific-expectations), [Use of AI tools](#use-of-ai-tools), [Our commitments as maintainers](#our-commitments-as-maintainers), [Reporting a concern](#reporting-a-concern) (in part) and [Appeals](#appeals), and adapted the examples and enforcement guidelines to the project.

Community Impact Guidelines were inspired by [Mozilla's code of conduct enforcement ladder](https://github.com/mozilla/diversity).

For answers to common questions about this code of conduct, see the FAQ at <https://www.contributor-covenant.org/faq>. Translations are available at <https://www.contributor-covenant.org/translations>.
