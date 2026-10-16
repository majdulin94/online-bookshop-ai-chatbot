# Chatbot UX restoration

The concise welcome wording and its three reading examples were recovered from
original commit `f7d295f`. The factual “AI-assisted” disclosure is retained.
The welcome contains no account name or payment/order/return example list.

The original code saved a welcome as an assistant message and also returned a
separate welcome banner. New sessions now use only the banner. History responses
omit recognized leading generated welcomes from old sessions, retaining stored
transcripts and ordinary assistant replies. Both guest and account history
loaders render exactly one welcome through the existing safe formatter.

The original mapping, present in commit `2780a86` and subsequent history, remains
unchanged: **Positive → 🙂, Negative → 🙁, Neutral → 😐**. There were no separate
historical emojis for motivation or curiosity.

The cleanup provider reports disabled/unavailable services as `Neutral` plus
`unavailable` metadata. Sentiment analysis now recognizes that metadata instead
of treating it as a genuine Neutral classification. A local keyword fallback
uses the project's existing mood vocabulary only when classification is
unavailable, invalid or raises an exception. This fallback is new; no historical
offline classifier was found. Valid provider classifications remain authoritative.
Curiosity/interest recommendations now run the same sentiment analysis as the
other recommendation branches, once per request.

Recommendation categories, topics, interest precedence, query construction,
filters, public catalogue and prices are unchanged. In particular, the mixed
“down and bored” prompt retains the original self-help recommendation priority.

Security behavior is retained: safe DOM rendering, same-origin link checks,
CSRF, ownership, request validation/limits, rate limits, provider timeouts and
error handling, and all payment checks. No service credentials are needed for
local verification. The local keyword fallback is intentionally limited to
recognized mood words; live model output can differ.

Validation includes eight new Django UX tests and four new DOM tests, alongside
all existing tests. The six requested prompts are also exercised over real local
HTTP with the public catalogue, CSRF cookies and external services disabled.

## Observed local response headers

External services were disabled. Each real HTTP reply returned three public
catalogue books and was rendered through the actual safe JavaScript formatter.

| Prompt | Header with rendered sentiment emoji |
| --- | --- |
| I feel sad | I'm sorry to hear you're feeling sad. Here are some Lifestyle & Self-Help books that might help: 🙁 |
| I feel happy | Thanks for sharing! Here are some Novels books that might help: 🙂 |
| I'm bored | Thanks for sharing. Here are some Novels books that might help: 😐 |
| I feel very motivated to start a new project | Thanks for sharing! Here are some Business books that might help: 🙂 |
| I'm curious about new technologies | Thanks for sharing! Here are some Science books that might help: 🙂 |
| I'm feeling a bit down and bored today. Can you suggest some entertaining books? | I'm sorry to hear you're feeling down. Here are some Lifestyle & Self-Help books that might help: 🙁 |

All **89 Django tests** (81 existing plus eight new), **23 chatbot-specific
Django tests**, **nine DOM tests** (five existing plus four new), and **21 HTTP
smoke checks** passed. Privacy/secret scans passed. No public catalogue changes,
original source/Git metadata changes, commits or pushes were made.
