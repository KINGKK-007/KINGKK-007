# Ghost in the Terminal — implementation and visual review

Reviewed on 9 October 2026.

## What was verified before editing

The profile repository is `KINGKK-007/KINGKK-007`. The complete README, SVG assets,
typography renderer, statistics generator and refresh workflow were inspected.
The published GitHub profile was opened in Chrome at desktop and mobile widths;
its actual README screenshots were reviewed.

The starting profile had a long image-based biography, oversized gaps, undersized
labels, a weekly histogram repeating the contribution grid, and four equally
weighted project tiles below the statistics. PitchPerfect was not featured.
The Tools & Data label used a different rendering path from its neighboring labels.

## Implemented design

- The hero keeps the planet, orbital rings and contour terrain. The name is
  stronger, the role and college are readable, and the terminal signature is
  specific to Kanav. The existing hooded, mint-outlined account avatar is preserved.
- A short, selectable introduction retains cricket, gym, travel, jerseys and the
  series joke. The Ctrl + Z line closes the page with the original sign-off.
- PitchPerfect is a broad featured card with its verified stack and an
  interview-specific microphone/waveform illustration. Three smaller project
  cards follow, with distinct but consistent line icons and source links.
- The toolkit is a single capability panel with three categories. The primary
  frameworks receive a restrained accent; every technology retains its name and
  monochrome icon. Small screens use a readable two-column arrangement.
- LinkedIn and email have higher priority. All existing social destinations remain.
- Dated activity and language snapshots share one visual system with the framed,
  annual snake. The calendar includes truthful month positions and a mint legend;
  empty days remain empty. Reduced-motion users receive the unchanged static cells.
- Achievements remain genuine. HackXIOS's measurable placement receives a modest
  emphasis, while both finalist results remain easy to scan.

## Project evidence and deployment checks

| Project | Primary evidence | Displayed stack / link decision |
| --- | --- | --- |
| PitchPerfect | [README](https://github.com/COolAlien35/PitchPerfect/blob/main/README.md), root `package.json`, `backend/requirements.txt` | Next.js, FastAPI, PostgreSQL, Redis, Docker; Gemini and Whisper appear in the desktop feature metadata. The repository lists no frontend deployment. Its example `api.pitchperfect.app` did not resolve, so no demo URL was invented. |
| Mini-Swiggy | [README and server source](https://github.com/KINGKK-007/Mini-Swiggy) | C, pthreads, TCP and IPC, including synchronization and file locking. |
| SignBridge 3D | [README and package manifest](https://github.com/DayalGupta03/Sign_Bridge1), repository homepage | Next.js, Gemini and MediaPipe. [The live deployment](https://sign-bridge1.vercel.app) returned 200 with the SignBridge title. This checks the deployment/landing page, not a camera-and-AI end-to-end session. |
| SmartCampus | [README and Maven manifest](https://github.com/Jdsb06/SmartCampus) | Spring Boot, MySQL and Flyway; the description reflects enrollment, notifications and events. Its Render homepage timed out during checking, so no live-demo button was added. |

X, Instagram and DEV returned successful responses; Twitter redirected to the
canonical X URL, which is now used. LinkedIn blocked automated checking with HTTP
999. The existing, resume-provided LinkedIn URL is preserved. Email is a mailto link;
no message was sent and mail delivery was not tested.

## Statistics decisions and reliability

The reviewed snapshot had **97 contributions and 33 active days**. These are
fetched values, not constants in the artwork. Publication and subsequent scheduled
runs can update them. The snapshot date is visible.

Retained:

- Contribution count and active days from the public GitHub calendar, when both
  meet the existing minimum of ten.
- Up to four languages with at least 2% of owned, public, non-fork project code
  bytes. The current distribution has four substantive shares, followed by a tail
  below 2%; displayed shares are not renormalized. The profile repository itself
  is excluded to prevent the renderer from influencing its own language chart.
- The original annual snake, reframed without inventing or moving contribution
  cells. Month labels use the actual calendar bounds and the generator's weekly
  columns. The displayed graph remains sparse because the underlying data is sparse.

Removed the redundant weekly histogram, negligible language shares, decorative
section numbering, the large biography image and the wall of individually boxed
technology badges. No follower, star, rank, streak or trophy-service widget was added.

README images are self-hosted, committed snapshots. The existing twice-daily
workflow generates the snake and the statistics, validates them, publishes the
output assets, and updates only `assets/stats/` on main using the GitHub Actions bot.
A newer design commit prevents an older run from overwriting its snapshots.
A failed fetch/render leaves the previous, dated, committed snapshot intact.
There is no picture-element HTTP-failure "fallback" assumption: the displayed
images already exist in the repository.

## Second-pass refinements from rendered output

The first redesigned draft was inspected in the actual GitHub profile DOM using
GitHub-rendered HTML and GitHub's own styles. The review found and fixed:

1. A live-demo arrow colliding with the last letters of its label.
2. Cramped secondary-project stack lines and excess space in the mobile feature.
3. A PostgreSQL label touching the neighboring MySQL icon on mobile.
4. Small snapshot metadata and insufficient annual-calendar context.
5. A white hero appearing on a dark GitHub page when OS and GitHub theme choices
   differed. Graphics now preserve the charcoal identity in all theme combinations.
6. A desktop asset becoming too small in the 1024px layout's 590px README column.
   Compact variants preserve readable type instead of merely shrinking the artwork.
7. Inconsistent hero/panel widths and mobile image upscaling. Intrinsic SVG sizing
   and simple centered markup keep the large panels aligned without custom CSS.
8. The first live publication loaded old cached graphics at unchanged asset URLs.
   The design generator now gives static image references content fingerprints,
   so updated artwork gets a fresh URL. Data snapshots retain their dated, stable
   URLs and can briefly show the preceding valid snapshot while caches refresh.

The responsive review covers 1440, 1024, 600, 390 and 320px viewports, plus light
mode and OS-light/GitHub-dark mode. Native headings and paragraphs inherit GitHub's
own styles. Fixed-width secondary cards wrap naturally into three, two or one column.
Full-article captures hide only GitHub's sticky navigation to avoid obscuring the
hero; no extra stylesheet or JavaScript is shipped in the README.

## Published verification

The **actual published profile**, with no replacement README HTML or local asset
interception, was inspected in Chrome at all five widths and both theme scenarios.
The complete desktop and mobile captures, compact layouts and narrow-phone output
were visually reviewed. All 18 displayed images loaded in every case, the expected
responsive variants were selected, and there was no horizontal page overflow.
The loaded static artwork matched the committed source files byte for byte.

The first redesign's final refresh recorded 99 contributions and 33 active days. During the live
review, the desktop overview briefly served the preceding valid 98-contribution
snapshot, while compact and mobile showed 99. The cached image was checked against
its actual previous repository version; it was not treated as a failed fetch or
claimed to be the newest snapshot. GitHub's image response advertises a 300-second
cache lifetime. Subsequent contributions and scheduled refreshes can change the
numbers again.

Validation passed: eight statistics regression tests, Python syntax, all 50 SVGs,
all 30 README image references, preserved GitHub-sanitized image URLs, stable
artwork fingerprints, and outlined text bounds. The snake animated in Chrome;
enabling reduced motion stopped the animation. Both publication workflows passed,
including the bot's update of the committed snapshots. The final
[refresh run](https://github.com/KINGKK-007/KINGKK-007/actions/runs/37873539565)
completed successfully.

## Wider project cards and readable details

The follow-up replaces the three narrow secondary tiles with two 400px desktop
cards: SmartCampus and SignBridge on the first row, then Mini-Swiggy centered below.
PitchPerfect spans the full README column. Each secondary card uses its own native
GitHub table container, allowing the complete card and its actions to wrap together
on phones rather than making a fixed two-column table scroll horizontally.

SignBridge now has separate, genuine **Source** and **Live demo** links inside its
footer. The old detached demo badge was removed. The footer graphics are adjacent
without whitespace so their two 50%-width actions stay on the same line.
Native GitHub styles provide the secondary cards' frames; the SVG content and
actions retain charcoal backgrounds, pale mint accents and the existing fonts.

Secondary descriptions use 16.5px type, technology lines use 14px, and actions use
14px. Dedicated compact, phone and narrow-phone assets preserve readable type.
Technology names wrap as complete items without trailing dot separators.
PitchPerfect's metadata increased to 13.5px. Toolkit category labels increased to
14px and technology names to 16px, with category headings above their items and
32px row spacing. Compact and phone layouts use more rows instead of compressing
all the items into one line.

The GitHub-sanitized preview was inspected in the actual profile DOM at 1440, 1024,
600, 390 and 320px, including light and mixed themes. Checks confirmed two secondary
columns above 480px, one column on phones, aligned source/demo actions, no card or
page horizontal overflow, and no clipped SVG text. All 54 local image references
resolve, and regenerating the artwork produces the same files and URL fingerprints.

## Remaining platform/account limits

- The actual sidebar bio is a separate account setting. The available GitHub
  authorization could not edit the profile API (HTTP 404); the placeholder was not
  overwritten. Update it at [GitHub profile settings](https://github.com/settings/profile):

  `CS @ IIIT Bangalore · Systems, AI/ML & backend engineering`

- GitHub controls the page chrome, native prose font and responsive column width.
  Graphic fonts are outlined SVG paths, so no external web-font loading is required.
  Graphic text is not selectable; useful alt text accompanies it.
- A full 53-column annual grid becomes small on phones. The graphic links to its
  full-size SVG. The design does not crop out inactive months to make activity seem better.
- LinkedIn's account page remains a manual verification because it blocks the
  automated request. No verified PitchPerfect frontend demo URL was available.
