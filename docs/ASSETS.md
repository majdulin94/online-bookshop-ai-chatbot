# Restored original assets

The original design is restored; no generic replacement SVGs remain.
See [attribution and the current watermark review](ATTRIBUTION.md).
The machine-readable [inventory](ASSET_INVENTORY.json) pins all reviewed assets.

Exactly these 27 original static assets were restored without changing their bytes:

- `myshop/static/animations/book-search.json`
- `myshop/static/animations/book-search01.json`
- `myshop/static/animations/bookshop-logo.json`
- `myshop/static/animations/chatbot-animated.json`
- `myshop/static/animations/chatbot-animated01.json`
- `myshop/static/animations/chatbot-titel.json`
- `myshop/static/animations/chatbot-titel01.json`
- `myshop/static/animations/chatbot-titel02.json`
- `myshop/static/images/books.jpg`
- `myshop/static/images/categories/arts-design.jpg`
- `myshop/static/images/categories/biography-autobiography.jpg`
- `myshop/static/images/categories/business.jpg`
- `myshop/static/images/categories/education.jpg`
- `myshop/static/images/categories/health-medical.jpg`
- `myshop/static/images/categories/history-politics.jpg`
- `myshop/static/images/categories/language-literature.jpg`
- `myshop/static/images/categories/library-reference.jpg`
- `myshop/static/images/categories/lifestyle-self-help.jpg`
- `myshop/static/images/categories/novels.jpg`
- `myshop/static/images/categories/other.jpg`
- `myshop/static/images/categories/philosophy-religion.jpg`
- `myshop/static/images/categories/science.jpg`
- `myshop/static/images/categories/social-sciences.jpg`
- `myshop/static/images/categories/technology.jpg`
- `myshop/static/images/default_profile.png`
- `myshop/static/images/logo.png`
- `myshop/static/images/placeholder.jpg`

Original CSS, font, Lottie initialization, image fallbacks and category-image
references are restored. The static default profile image is included; private
profile uploads, PDFs and recordings remain excluded.

The user-approved `data/public_catalogue.json` restores **3,260 public book
records**, including **3,171 original Google Books cover URLs**. The other 89
records reference the original `images/placeholder.jpg` fallback.
`data/public_categories.json` preserves all **15 category names and their
original display order**. No generic replacement artwork is used.

Only public bibliographic/catalogue fields were selected from Book/Category
tables. Original database IDs, accounts, orders, reviews, uploads and credentials
were excluded. Three email occurrences in book descriptions were replaced with
`[contact omitted]`; the remaining public fields and cover references are intact.
Prices and availability are original project demonstration values.

At the start of chatbot UX work, the extracted publication copy already
contained an edited `technology.jpg` and a replacement `history-politics.jpg`.
Both files were preserved without modification; their reviewed hashes are now
recorded in the inventory. The current history image has no visible watermark.
The technology image still has repeated Shutterstock watermarks. Earlier
restoration/hash and 123RF notes describe the prior original-asset snapshot.
