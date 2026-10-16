# Restoration validation — October 16, 2026

The restored application runs with Python 3.11.12 and the credential-free
`myshop.test_settings`. Current checks:

- **89 Django tests passed (81 existing plus eight chatbot UX regressions)** on isolated SQLite after the public-catalogue seed change.
- **9 JavaScript/DOM tests passed (five existing plus four UX regressions)** with Node.js/jsdom against restored scripts.
- **21 live HTTP smoke checks passed**, including expected payment rejections.
- Fresh migrations and static collection passed.
- Publication scans cover source, documentation, image metadata and animations.
- Separate private checks compare against 14 known team-identity patterns and
  six current/historical secret patterns, without publishing those values.
- All 27 restored static assets have the same SHA-256 hashes as the original.
- Original source and Git metadata are checked against 1,344 pre-change hashes.

## Visual comparison

Local headless Chrome captures use a 1440 × 1100 viewport. The restored app is
compared with the original project's templates and static assets, rendered with
the same approved public catalogue (3,260 original book records and 15 categories). Homepage hero, logo, gradients, fonts,
navigation, category artwork, catalogue cards and Lottie animation references
are restored. Animation frames can differ between captures.

Each homepage, catalogue and homepage-category comparison had **zero changed
pixels across 1,216,800 compared pixels**. The compared rectangle was
`x=0..1199, y=86..1099`, excluding the navbar and the independently timed chatbot
overlay. The navbar and animations were inspected visually. All 27 restored
static assets were also served successfully over HTTP and matched their hashes.

The footer retains sanitized contact text. Only public Book/Category fields
were exported, with no original database IDs or private user tables. Three email
occurrences in book descriptions were redacted. All 3,171 Google Books cover URLs
and 89 original fallback references were preserved. Catalogue field equality,
category display order and repeat-seed idempotence are checked in the isolated
database. External CDN and cover requests need network access.

Fifteen embedded raster images in the Lottie files were visually inspected:
they depict illustrated books and robot parts, with no private uploads found.
Artist credits in original image metadata are preserved as third-party
attribution. The two visible stock-watermark issues are listed in
[ATTRIBUTION.md](ATTRIBUTION.md).

## Publication scope

`docs/PUBLICATION_FILES.txt` defines the export. The verifier reads working
publication files, checks reviewed asset hashes, scans metadata/text and rejects
unexpected publication files. Local `.env`, virtual environments, validation
databases, preview profiles/logs and Git metadata are excluded from the export.
Local configuration is left in place for the developer and must not be uploaded
by copying the entire working directory. The clean publication archive contains
only the allowlisted files, with no Git history or remote configuration.

Live OpenAI, Stripe, SMTP and Google Books API integrations were not exercised;
external service calls are disabled in isolated settings. Public cover images
and UI CDN assets were loaded for browser captures. The current restoration did
not rerun the previous PostgreSQL validation. No commit or push was performed.

Scans and visual inspection reduce privacy risk; they cannot prove the absence
of every possible issue. Recheck final publication bytes if files change.

The subsequent [chatbot UX restoration](CHATBOT_UX.md) preserves the original
three sentiment emojis and restores one concise welcome. Chatbot-specific
Django tests, live local prompt checks and HTTP smoke checks are included.

At the start of chatbot UX work, the extracted publication copy already
contained an edited `technology.jpg` and a replacement `history-politics.jpg`.
Both files were preserved without modification; their reviewed hashes are now
recorded in the inventory. The current history image has no visible watermark.
The technology image still has repeated Shutterstock watermarks. Earlier
restoration/hash and 123RF notes describe the prior original-asset snapshot.
