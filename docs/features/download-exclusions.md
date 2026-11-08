# Download exclusions and attempt budgets

Administrators can stop retrying a track from its active or failed queue row.
This stores an exclusion across restarts without deleting existing audio.
Open the exclusions panel in Queue to allow downloads again; this does not
start a download. A transfer still stopping must finish before it can resume.

Downloads settings optionally set a cumulative attempt budget in minutes.
The default is zero (disabled). Time waiting between monitor checks does not
count. Failed attempts accumulate; successful downloads reset their budget.
Artist releases reset it only after the file validates against that release.
Identity matching preserves remix/live qualifiers and refuses ambiguous matches.

Checks run at provider boundaries, progress updates and Deemix/slskd polling.
They are cooperative: an outstanding network request may finish first.
The setting is not a hard process deadline and does not cancel shared remote
Deemix/slskd transfers, which may be used by another application.

Administrators control exclusions globally for this server. Standard users and
signed audio URLs cannot change them. Existing exclusions also apply when the
time budget is disabled. The SQLite journal is in the monitor database.
