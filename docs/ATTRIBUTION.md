# Original project assets and attribution

The university project's original presentation assets are preserved. They are
third-party material where applicable; inclusion is not a claim of authorship
or a blanket license grant. Missing licensing records alone were not grounds
for removing or replacing an asset.

The exact restored paths, SHA-256 hashes and available provenance are recorded
in [ASSET_INVENTORY.json](ASSET_INVENTORY.json). All 27 restored static files
are byte-for-byte copies of the original local project. Existing metadata and
visible credits are retained. Private profile uploads are excluded; the static
default-profile graphic is a project UI asset.

| Material | Available provenance |
| --- | --- |
| Hero `images/books.jpg`, logo `images/logo.png`, default profile and fallback cover | Original project static directory; upstream creator/source not recorded |
| Fifteen category images | Original project category directory; filenames and metadata retained |
| `categories/biography-autobiography.jpg` | EXIF Artist: Zolak; description: “Biography word written on wood block, life concept.” |
| `categories/novels.jpg` | EXIF Artist/XPAuthor: Abhi Sharma; description “Books HD” |
| `categories/language-literature.jpg` | Depicts *Language & Literature: A Practical Guide, Student Book*, IB Skills; the cover credits Mike East, Nevine El Souefi, Graham Maclure and Chad Swabey |
| Eight Lottie JSON files | Original project animations; several contain LottieFiles exporter metadata, which identifies tooling rather than proving authorship |
| `book-search.json` | Internal name “Main Scene”; LottieFiles Creator exporter |
| `chatbot-animated.json` | Internal name “Bot Say Hello”; LottieFiles toolkit exporter |
| `chatbot-animated01.json` | Internal name “bot 01 12 thanks”; LottieFiles toolkit exporter |
| Bootstrap 5.3.3 | CDN dependency; [upstream notice](https://github.com/twbs/bootstrap/blob/v5.3.3/LICENSE) |
| Font Awesome Free 6.5.0 | CDN dependency; [upstream notices](https://github.com/FortAwesome/Font-Awesome/blob/6.5.0/LICENSE.txt) |
| Lottie Web 5.12.0 | CDN dependency; [upstream notice](https://github.com/airbnb/lottie-web/blob/v5.12.0/LICENSE.md) |
| Pacifico | Original Google Fonts stylesheet restored; [font source and notice](https://github.com/google/fonts/tree/main/ofl/pacifico) |
| Original catalogue covers and descriptions | Public bibliographic snapshot in `data/public_catalogue.json`: 3,260 books, 3,171 original Google Books thumbnail URLs and 89 original fallback references. The covers/descriptions remain material of their respective creators/publishers; covers load from Google Books and are not redistributed as downloaded files. Three email occurrences were redacted. |

## Assets requiring manual review

Only the following restored assets showed a clear watermark problem during
visual inspection. Both remain in place to preserve the project's presentation.

| File under `myshop/static/images/categories/` | Visible evidence | Review needed |
| --- | --- | --- |
| `technology.jpg` | Repeated Shutterstock watermarks; footer image ID **2284126663** | Confirm the project's license or obtain the corresponding authorized asset before public release |
| `history-politics.jpg` | Repeated **123RF** watermarks | Confirm the project's license or obtain the corresponding authorized asset before public release |

No other restored asset is flagged merely because its source or license is
unrecorded. No watermark has been cropped, removed or obscured.

At the start of chatbot UX work, the extracted publication copy already
contained an edited `technology.jpg` and a replacement `history-politics.jpg`.
Both files were preserved without modification; their reviewed hashes are now
recorded in the inventory. The current history image has no visible watermark.
The technology image still has repeated Shutterstock watermarks. Earlier
restoration/hash and 123RF notes describe the prior original-asset snapshot.
