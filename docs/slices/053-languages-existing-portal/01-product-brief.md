---
slice: 053-languages-existing-portal
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-27
status: draft
inputs:
  - "docs/slices/046-redesign-wave5/* (on branch slice/046-redesign-wave5, read in full)"
  - "docs/slices/009-ess-portal-redesign/01b-ux-design.md, 00-assessment-and-plan.md, appendix-a-frame.md"
  - "docs/slices/008-field-checkin/01-product-brief.md, 01c-security-privacy-requirements.md"
  - "docs/slices/013-mobile-app/01-product-brief.md"
  - "docs/priorities/2026-09-18-priority-order.md"
  - ".claude/context/product-context.md, security-compliance-baseline.md, handoff-contract.md, definition-of-ready-done.md"
missing_inputs:
  - "01a-ux-opportunities.md for this slice — NOT written. See 'Two inputs are missing' below."
  - "07-devops-inputs.md §1 for this slice — NOT written. Wave 5's 07 was read instead."
---

# Slice 053 — Hindi and Punjabi on the portal we are keeping

## Bad news first, in three lines

**1. The screen you asked me to translate is the hardest one in the product to translate, and the people who need the language are not on it.** The existing portal has **13,459 lines of JavaScript with exactly one translatable string in it** (Confirmed: `alvoraa_portal/public/js/ess/portal.js`, one `__()` call at line 3742) and **zero translatable strings in its twelve Jinja fragments and its page** (Confirmed: `_(` appears 0 times in `templates/includes/ess/parts/*.html`, 0 times in `www/hrms-employee.html`; the only 14 in the whole `ess/` tree are in `next/frame.html`, which is the frame you discarded).

**2. We are already shipping unreviewed machine-translated Hindi to frontline workers, today, on a production surface.** `alvoraa_portal/www/field-checkin.html` carries an EN / हिं switch and about **75 Hindi strings** — including the whole DPDP privacy notice — under a comment in our own code that says: *"The Hindi column is a MACHINE DRAFT and must be checked by a native speaker before it is switched on for a customer."* (Confirmed, lines 473–554.) It was never checked, and the switch is on screen, not gated. Your first client goes live in early October.

**3. Meanwhile the field app — the surface built for Hindi-first workers — ships English only.** The language row in `mobile/field-app/web/js/checkin.js` (lines 593–620) is a **debug-only, disabled scaffold** whose own comment says *"No screen has Hindi text yet."* Slice 013's brief promised *"Language once, everywhere — read the app in Hindi — Yes"*. That promise is not kept.

**My recommendation in one line:** do **not** rewrite Wave 5 for the old portal yet; spend a much smaller slice getting the Hindi we already show to frontline workers **reviewed by a named human or taken off the screen**, and keep Wave 5's machinery on the shelf for the portal until a customer's office staff actually asks for it.

You decide. If you want the portal anyway, section 7b gives you the smallest honest version of it.

---

## Two inputs are missing, and you should know before you read further

The handoff contract says a brief is written **after** the UX opportunities scan (`01a`) and DevOps' first look (`07` §1) for this slice. Neither exists for 053. I did not stop, because the product question you asked — *how much of this is worth doing* — can be answered from the measurements you supplied plus Wave 5's own paid-for documents, and because stopping would leave point 2 above sitting on a live site. **But two consequences travel with this brief:**

- the persona table in section 5 is assembled from slice 009's design document and slices 008/013, not from a fresh scan — I have labelled it;
- the effort and run-cost figures are **Wave 5's**, for Wave 5's frame. Nobody has estimated the retro-fit. That is the single biggest unknown in this brief and I have not guessed it.

---

## 1 · The job to be done

> **"I check in at the gate on my own phone. I want to read what the app is recording about me, and mark my attendance, in Hindi — because I read Hindi, and the screen decides whether I trust you."**
> — a frontline retail employee, Chandigarh. The words are mine, built from slice 009's persona (`01b` §Rahul Kumar) and slice 008's field persona. **Needs validation** with one real person.

**Persona:** Employee (own record only), specifically the **frontline / shift employee** in `product-context.md` §2 — *"Shared or low-end phone, poor connectivity… their own language."*

**What changes for the other two:**

- **HR Manager** — gains a thing to say to a customer's plant HR: *"your workers read the consent notice in their own language, and a named person signed off the wording."* Loses nothing.
- **CXO** — no effect on any number they look at.

---

## 2 · The current pain, in numbers and in one story

| Thing | Number | Label |
|---|---|---|
| Translatable strings in the existing portal's JavaScript | **1** in 13,459 lines | Confirmed, grep, 2026-09-27 |
| Translatable strings in the existing portal's Jinja (12 parts, ~1,575 lines, + the page + old `frame.html`) | **0** | Confirmed, grep |
| Translatable strings in the frame you discarded | **243** `__()` + 14 Jinja `_()` | Confirmed (your measurement; 046 `00b` counted 76 in `next-frame.js` alone) |
| Strings in Wave 5's catalogue | **1,593** (046's own `main.pot` records 1,473 ids for the app) | Confirmed from 046 docs |
| Hindi or Punjabi written by a human for the portal | **0 words.** `hi.po` and `pa.po` carry one entry each | Confirmed, 046 `03` §"Not one word… was fabricated" |
| Frappe HR's own Hindi catalogue | **2,243 ids, 853 filled — 38%** | Confirmed, 046 `00b`, counted on a bench |
| Punjabi anywhere in the stack | **Does not exist.** `pa` is absent from Frappe's 83-row `languages.csv`; no app ships a `pa.po` | Confirmed, 046 `00b` B2 |
| Machine-draft Hindi strings live on the frontline check-in page | **~75**, including the privacy notice | Confirmed, `field-checkin.html` 473–554 |

**The story.** A worker at the gate opens the check-in page. He taps हिं. He reads a privacy notice in Hindi that nobody who speaks Hindi has ever read. If one line of it is wrong — say the line about what we do **not** record — he has been told something untrue about surveillance, in his own language, by his employer's software. That is the cheapest possible way to lose the trust the whole product is built on. **No data: I do not know whether any worker has ever tapped it**, because nothing counts it.

---

## 3 · Competitive analysis — whole products

| Capability | Keka | Zoho People | Darwinbox | Frappe HR standard | CatalystOne | Us today |
|---|---|---|---|---|---|---|
| Employee portal in Indian languages | Multi-language employee portal, Indian languages included, on paid tiers `[recall — verify]` | Multi-language across the Zoho suite, standard in the plan `[recall — verify]` | Many languages, sold hard to enterprises with plant workforces `[recall — verify]` | **Real and free:** 34 language catalogues ship with `hrms`; Hindi 38% filled | Nordic/European languages first `[recall — verify]` | English only. One translatable string in the portal |
| Frontline mobile app in a local language | Yes, mobile app localised `[recall — verify]` | Yes `[recall — verify]` | Yes, and it is a named reason they win plant deals `[recall — verify]` | Frappe HR mobile PWA inherits the catalogues — **so a Frappe HR customer gets partial Hindi for free, and our portal gives them less** (read, 046 `00b`) | — | English only; a disabled debug scaffold |
| Who writes the words | Vendor, professionally `[recall — verify]` | Vendor `[recall — verify]` | Vendor `[recall — verify]` | Community, unevenly — `ta.po` has 2,172 ids and **zero** translations (Confirmed, 046 `00b`) | Vendor | Nobody |
| Customer can correct a word without waiting for us | Unknown | Unknown | Unknown | **Yes** — a `Translation` row overrides the catalogue, takes effect on the **next request**, per site, no deploy (Confirmed by execution across two processes, 046 `00b` B3) | Unknown | Inherited, unused |
| How it is sold | Bundled | Bundled | Bundled | Free | Bundled | — |

**What we will deliberately NOT do, and why it makes us better for this user:**

1. **We will not ship a language nobody has read.** Every competitor above ships more languages than we do. None of them can tell a customer the name of the person who read the Hindi. Wave 5 already invented the gate for this (`REVIEWED_LANGUAGES`, empty until a human signs); it is the one thing here worth keeping whatever you decide.
2. **We will not chase language count.** `product-context.md` §6 item 10 — no feature-parity race. Two languages read by real people beat ten machine-drafted ones, and `ta.po` is the standing proof that a shipped language can be worth nothing.
3. **We will not machine-translate at run time.** No AI in this slice, no translation API, no model client (Wave 5 made that structural: nothing imports one).
4. **We will not translate the desktop portal to look complete.** A half-Hindi screen is a worse product than an English one. Section 6 draws that line.

---

## 3a · Three ways to do this, and the one I propose

**A · Conventional — port Wave 5 to the old frame.** Wrap ~1,500 strings across `portal.js` (13,459 lines) and 12 Jinja parts, add the switch to the old frame, fill both catalogues, ship. Wave 5's own estimate for the *easy* frame was **4–6 days plus review** (`docs/priorities/2026-09-18-priority-order.md`, item 18). The retro-fit is a separate, unestimated cost on top, in the hottest file in the repo — the work board shows five sessions have queued on `portal.js` in the last fortnight. **Risk: a 1,500-string mechanical edit through a file other people are editing.**

**B · Better — keep Wave 5's server side, translate only the journeys people finish.** Wave 5's server half is frame-independent: `language_api.py`, the narrowed page dictionary (168 ids, **326 gzipped bytes** measured, against 92 KB for the naive version), the reviewer gate, the escaping rule and three CI checks. None of that needs rewriting — only the switch control and the string wrapping are frame-specific. Wrap the nav plus Home plus the leave/attendance request flow, ship **Hindi only**, and carry Wave 5's derived honesty line ("some words are still in English"). Smaller, but still a multi-hundred-string retro-fit, and the nav is shared so every other screen shows Hindi chrome over English content.

**C · Reimagined — put the language where the reader is.** The person who needs Hindi is holding a phone at a gate, not a laptop at a desk. Translate the **frontline surfaces** (the check-in page and the field app's join/notice/check-in screens — about 75–120 strings that are **already in a string table**, no retro-fit at all), get them reviewed by a named human, and leave the desktop portal in English until a customer's office staff asks for Hindi. **Kano-wise this is also where the class is highest** (section 4).

**Could we not build this at all?** For the **portal** — yes, today, at no cost: no customer has asked, and nothing is broken by leaving it English. For the **frontline** — no. Doing nothing leaves unreviewed machine Hindi on a privacy notice on a site that goes live next week. The smallest possible move there is not a feature at all: **review the 75 strings, or delete the switch.** That is a morning's work and it is the thin slice.

**I propose C, starting with the review-or-remove move.** Wave 5's branch is not wasted — it is banked, and section 7b says exactly what to reuse if you choose A or B later.

---

## 4 · Kano class and demand — honest about what is real

All **proxy**, no survey. Nobody has run the two-question survey on this.

| Candidate | Class (proxy) | Why |
|---|---|---|
| **Local language on the frontline check-in / field app** | **Must-be** where the workforce is Hindi-first | All reference competitors have a localised frontline app; Frappe HR itself gives partial Hindi free; and DPDP expects the notice in a language the person reads (section 10). Its absence is felt as "this is not for me" |
| **A translation a named human accepted** | **Attractive** | Nobody else offers it. It is our whitespace shape — evidence-first, applied to words |
| **Unreviewed machine Hindi on screen** | **Reverse** | A Hindi reader who meets clumsy Hindi trusts us **less** than if the screen had been English. This is the only Reverse item I have ever put in a brief about a feature we already ship |
| **Hindi on the desktop employee portal** | **Indifferent today, Performance later** | Indian mid-market office staff use English HR portals. I have no request, no lost deal and no ticket asking for it |
| **Punjabi, anywhere** | **Indifferent until a named customer needs it** | The only Punjabi evidence in this repo is one line in a PP Jewellers job advert (`docs/pp_jewellers/06`) and a persona sketch. `pa` does not exist in Frappe at all, so it costs more than Hindi and has less behind it |

**How much demand is real?** Almost none is customer-verified, and I will not dress it up.

- **Confirmed:** one live client tenant (`dtc`, going live early October) and demo tenants (`ppj`, Sargam). **Evidence required:** whether `dtc`'s workforce is office staff or frontline, and what they read. **I could not check that — it needs you or the client.**
- **Read, dated:** our own design work assumed it — slice 009 `01b` (Sep 2026) put "Hindi or Punjabi" in the frontline persona and flagged the prototype's wording as machine-drafted; slice 008's `01c` (2026) called the Hindi/Punjabi notice "a DPDP expectation… weeks away, not quarters".
- `[recall — verify]` everything in the competitor table.
- **Not seen:** a single customer request, demo note or support ticket asking for Hindi. If one exists, it changes the ranking and I would like the date.

**What would change the class:** one Hindi-first frontline pilot group at `dtc` or `ppj` completing setup in Hindi versus English. Twenty people and two weeks would settle it.

---

## 5 · Persona enhancements — what is in this slice and what is not

`01a` is missing, so these ideas come from slice 009 `01b`, slice 008 and slice 013, labelled as such. Per the contract, I have decided each one.

| Persona | The idea | The job it serves | In this slice? | Why |
|---|---|---|---|---|
| **Frontline employee** (phone, gate) | The join, notice and check-in screens in reviewed Hindi, with the EN/हिं switch remembered on the device | "Tell me what you record about me, in my language" | **Yes — this is the slice** | The strings already exist in a table; the work is review, not invention |
| **Frontline employee** | The same on the installed field app (013), not only the browser page | One language wherever he opens it | **Later — second step, same slice family** | App text lives in JS files with no string table yet; and a correction needs a store release, not a deploy. Sequence it after the browser page proves the words |
| **Employee** (office, desktop portal) | Portal in Hindi | Read my payslip and leave balance in Hindi | **No, not now** | 13,459 lines with one translatable string; no evidence anybody has asked. Revisit when a customer does |
| **Line manager** | Approvals in Hindi | — | **No** | No evidence, and managers in our tenants work in English `[ASSUMPTION]` |
| **HR Manager** | A screen that says which languages are offered and who reviewed each one | Answer "is our workforce's notice in their language?" without asking us | **No — later** | Wave 5's `REVIEWED_LANGUAGES` is a code constant; a screen for it is a new settings page and section "anti-over-engineering" says no |
| **HR Manager** | Correct one wrong word on their own tenant, live | Fix "छुट्टी" to the word their plant actually uses | **No — later** | The mechanism exists and is proved (a `Translation` row, next request, no deploy). But Wave 5's decision D-5 said no tenant editing for v1, and letting a tenant write translation text re-opens a markup-injection path. Keep it as an internal correction route for now |
| **CXO** | — | — | **No effect** | Honest answer |

---

## 6 · What "done" means for a language — where the line is

**The unit of done is a complete journey on one surface, not a string count.** A screen that changes language mid-sentence is worse than English, because it reads as carelessness about exactly the person it was supposed to include.

Three rules I recommend you adopt and keep:

1. **No language is offered until a named human has read every string on the journeys it is offered for, and their name and the date are recorded.** This is Wave 5's `REVIEWED_LANGUAGES` gate. Keep it whatever else changes.
2. **A journey is done when every string a person meets between starting and finishing it is in their language** — the button, the error, the hint text and the notice. Data (names, amounts, dates) stays as it is; 046 already proved numbers, dates and money do not move.
3. **Where English will still appear — and it will, because Frappe HR's Hindi is 38% filled — the screen says so in one plain line.** Wave 5 derived that line from the catalogues rather than hard-coding a claim. Reuse it.

**And the corollary, said plainly: a machine draft is not done.** If nobody will read the 75 Hindi strings on the check-in page before `dtc` goes live, my recommendation is to **take the switch off the screen** and ship English. That is a smaller, safer product than the one we have today.

---

## 7 · The thin slice

### 7a · What I propose (option C, first step)

**One outcome, one person, end to end: a Hindi-reading frontline worker sets up his phone and marks his attendance, reading every word — including the privacy notice — in Hindi that a named person has read and accepted.**

**Needed to validate this now:**
- A named bilingual reviewer reads the ~75 strings in `field-checkin.html` and either accepts each line or rewrites it. HR words matter more than grammar: the reviewer should be someone who knows the plant's own vocabulary (a tenant HR person is better than a translator here).
- The accepted Hindi is recorded with the reviewer's name and the date, and the language is gated behind that record — nothing is offered without it.
- The existing escaping rule is carried over: **Frappe's Jinja does not escape automatically, so a translation is code.** Wave 5's own bench work proved `sanitize_html` lets `<b>` through. Every translated string is escaped at the render point, and the CI check that proves it comes across unchanged.
- The switch remembers the choice on the device, and the notice acknowledgement records which language the person read it in. *(This may already be partly true — the notice acknowledgement doctype exists. The analyst must check, not assume.)*

**Needed before it can ship:**
- The three CI checks from Wave 5, ported: escaping at every render point; no translation ships without a reviewer; the catalogue check that refuses markup a translation's own English source does not have. All three already exist and pass.
- A decision on what happens on the field **app** (013), which shows English while the browser page shows Hindi. Inconsistent is acceptable for a week; it is not acceptable as a resting state.

**Worth doing later:** the field app's own screens; the HR-visible "which languages, reviewed by whom" view; tenant-editable wording; Punjabi; the whole desktop portal.

**Not doing:** machine translation at run time; AI-drafted words shipped without review; translating anybody's typed content (goal text, feedback, comments) — that is somebody's writing, not our interface.

**Out of scope for this slice, explicitly:** `portal.js`, `hrms-employee.html`, the twelve `parts/*.html` fragments, the old `frame.html`, Punjabi, the field app's Android release, any new settings screen, any new doctype.

### 7b · If you choose the portal anyway — the smallest honest version

Say so and I will rewrite this brief around it. What I would recommend then, in order:

1. **Reuse, do not rebuild.** Wave 5's server half is frame-independent and already tested: `language_api.py`, the 168-id narrowed dictionary (**326 gzipped bytes** measured), the reviewer gate, the three CI checks, the `hi.po`/`pa.po` scaffolds, and the settled bench facts (a website page gets no dictionary unless its own controller emits one — about four lines).
2. **Hindi only.** Punjabi doubles the translation bill for no named customer, and `pa` does not exist in Frappe.
3. **One journey, whole:** the nav, Home, and the leave/attendance request flow. Everything else keeps its English until somebody asks.
4. **Wrap strings in the same commits as the screens they live on**, never as one 1,500-string sweep through `portal.js` while other sessions hold that file.
5. **Accept that the chrome will be Hindi over English content** on the untranslated screens, and show the honesty line. If that is not acceptable, the portal slice is not a slice — it is the whole retro-fit, and it should be priced as one.

---

## 8 · The WOW moment — exact screen, exact words

**Screen:** the field check-in "Before you start" notice, in Hindi, on a ₹7,000 Android phone at a factory gate.

**The moment:** under the heading **"हम क्या दर्ज नहीं करते"** ("What we do not record") the worker reads:

> **बीच के समय में कुछ नहीं। काम करते समय आप पर नज़र नहीं रखी जाती।**
> *("Nothing between punches. You are not tracked while you work.")*

**Why it lands:** every other attendance app he has used told him nothing, in a language he half-reads. This one tells him what it will **not** do, in his language, on the first screen, before he agrees to anything — and the wording was read and accepted by a person whose name we can give his HR manager.

**Achievable inside this slice:** yes. That string exists today (`field-checkin.html:494`). The slice is the review, the gate and the escaping — not the writing.

---

## 9 · The translation supply chain — the part that decides whether this is possible

This is the long pole, not the code.

| Question | Answer |
|---|---|
| **How many phrases?** | This slice: **~75** (the check-in page), plus ~40–120 if the field app follows. Confirmed by counting the string table. The portal: **~1,500**. Confirmed from 046's catalogue |
| **Who writes them?** | For this slice: nobody writes anything new. A bilingual reviewer **reads a draft and corrects it**. My recommendation: a tenant HR person (PP Jewellers or `dtc`) plus one of us, in one sitting, because HR vocabulary beats literary Hindi. For the portal's 1,500: a paid professional Indian-language HR translator. Machine draft first is fine **as a draft** |
| **Who checks them?** | One named person per language, recorded. Their name is the gate. **Open question: who? Only you can name them** |
| **What does it cost?** | This slice: **a morning of one bilingual person** — a working estimate, not a quote. The portal's 1,500 phrases: **Evidence required — a quote from one professional translator.** I will not invent a per-word rate |
| **How does a correction ship?** | **Three different answers, and the difference matters.** (a) Check-in page today: it is a server file — a correction needs a normal release. (b) Anything that goes through Frappe's `_()`: a **`Translation` row** on that tenant's site corrects the word **on the next request**, no deploy, no cache clear — Confirmed by execution across two processes (046 `00b` B3). (c) The installed field app: a **store release**. So put the words on paths (a) and (b) where you can, and keep app-only text to a minimum |
| **What if the reviewer never appears?** | Then the honest product is English. See section 6's corollary and the kill criteria |

---

## 10 · Regulatory read — four lines

1. **Which regime?** Data protection — **DPDP Act 2023**. Its notice duty expects the notice in English or a language of the Eighth Schedule; Hindi and Punjabi are both in it. Fiduciary duties phase in around **May 2027** (dated: baseline, 24 Aug 2026 — **re-check, it is over 90 days old**).
2. **Whose obligation?** **Our customer's**, as the employer. This slice is the better kind of feature: it helps them discharge their duty. That is what wins the security review.
3. **What does this slice make possible that was not?** No new data collected. One new personal preference the person sets about themselves. **One thing gets worse if we do nothing:** a notice in a language nobody verified is arguably not a *clear* notice. ⚠ **COMPLIANCE — decision owner: Surbhi, with counsel.** Question for counsel, one line: *if we offer a privacy notice in Hindi, does an inaccurate translation weaken the notice we rely on?* **I am not a lawyer.** What it blocks: whether the review must happen **before** `dtc` goes live or can follow it.
4. **The honest downside.** If the front page read *"HR software showed factory workers a machine-translated privacy promise nobody had checked"*, we could not defend it. That sentence is why this slice exists in this shape.

**Refusals, restated:** no AI drafting or ratings anywhere near this; no run-time machine translation; no translation of an employee's own words; nothing about who reads what language is shown to a manager (section 11).

---

## 11 · Thriving-workplace check

| Lens | One line |
|---|---|
| **Engagement** | A worker reads what his employer records about him in his own language, before he agrees to it. That is clarity and agency he does not have today |
| **Collaboration** | Small: a tenant HR person's knowledge of their own plant's vocabulary becomes the product's words, with their name on it |
| **Inclusiveness** | This *is* the inclusiveness slice — a Hindi-first worker on a cheap phone is the least-served person in our user list. It still excludes people who read neither Hindi nor English, and people with no smartphone; they keep the reception machine |
| **Transparency** | It makes an existing promise *readable*. **And a hard limit: a person's chosen language must never appear in any manager-visible list or report.** Language is a proxy for region, caste, class and migrant status. Wave 5 already refused this (nobody learns what anybody else reads); carry it forward. Adoption is measured as a **site-level count with a minimum of five, never per person** |

---

## 12 · Success criteria

| # | Measure | Baseline | Target | How it is instrumented |
|---|---|---|---|---|
| S1 | **Reviewed coverage** — share of Hindi strings on the offered journeys that a named human accepted | **0% today, for ~75 strings already on screen** (Confirmed by the code comment) | **100% before any language is offered** — a gate, not a dial | The reviewer record; the CI check that fails if a language is offered without one |
| S2 | **Adoption** — share of frontline users at one Hindi-first tenant who choose Hindi and are still on it after two weeks | **baseline unknown — measure first.** Nothing counts it | Set it after the first two weeks. A number below ~10% at a workforce HR calls Hindi-first is a finding, not a failure | Aggregate count of stored language per site, minimum n of 5, **never per person** |
| S3 | **Completion** — share of phone setups that reach "you are set up" without HR help, Hindi versus English | **baseline unknown — measure first** | Hindi no worse than English | The existing join/enrol funnel, split by chosen language, aggregate only |
| S4 | **Correction turnaround** — days from "that word is wrong" to the right word on screen | no route today | **one working day**, without a deploy, for anything on the `_()` path | Time-stamp the first real correction. Possible today: proved by execution (046 `00b` B3) |

**Banned here:** number of languages shipped, number of strings translated, page views. None of those is an outcome.

---

## 13 · Risks, red-teamed

| # | Risk | What breaks | Cheapest way to find out first |
|---|---|---|---|
| R1 | **The 1,500-string retro-fit of `portal.js`** | A mechanical sweep through the repo's hottest file, which five sessions have queued on this month, with no test that asserts a string is visible. Merge conflicts, silently dropped strings | Wrap **one** screen and count the hours. If one screen costs a day, 1,500 strings is not a slice |
| R2 | **Building the machinery again for a language nobody has written** | We spend 4–6 days plus a retro-fit and ship a switch that offers nothing, exactly as Wave 5 already does today, by design | Get one language reviewed **first**. Words before machinery. That is the order this brief proposes |
| R3 | **The unreviewed Hindi already on screen** | A worker is told something untrue about monitoring, in his own language, by his employer's software, a week before a real go-live | Read the 75 lines. One morning |
| R4 | **A translator injects markup** | Frappe's Jinja does not autoescape and `sanitize_html` permits `<b>`; a translation is a content channel on every page | Already solved: escape at every render point + the CI check. Carry both over unchanged. Do not relax |
| R5 | **Bad data / missing translation** | A missing translation is **invisible at run time** — no error, no log, no metric. "The portal is in Hindi" ships with nobody knowing how much of it is | Print the translated-ids-over-total figure in CI and put it in the release note (046 OPS-W5-14) |
| R6 | **10× scale** | The naive dictionary is **92 KB gzipped** of words no screen shows. Measured, and already designed out to 326 bytes by sending only the ids our own scripts can ask for | Keep the narrowing. Re-measure the day a real catalogue lands |
| R7 | **A tenant is not prepared** | A `Language` record may not exist on a tenant even after install — observed on a fresh bench. The row silently does not appear and it looks exactly like a bug | It is a release-checklist step, not code. Confirmed, 046 `00b` B2 |
| R8 | **Support tickets this would create** | "Why is half my screen in English?", "Who wrote this Hindi?", "My manager can see I use Hindi?" (the answer must be a flat no), "I corrected a word and nothing changed" (the source string must match exactly — Confirmed, 046 `00b`) | Answer all four in the release note before it ships |
| R9 | **A wrong bet on the screen** | We translate a desktop portal that Hindi-first workers never open | Ask `dtc`'s HR one question: how many of your people open the portal on a laptop? |

---

## 14 · Which of the four is this? (anti-over-engineering)

**Configuration and reuse, plus a small amount of new code.** No new module, no new dashboard, no new settings page, no new doctype, no migration, no AI. The correction route uses Frappe's own `Translation` doctype and its own cache invalidation — both already built, both proved on a bench. Wave 5's own verdict stands and is worth repeating: *"Wave 5 adds no second cache."* Keep it that way.

**Why the cheaper option was not enough:** the cheapest option — do nothing — is what leaves unreviewed Hindi on a privacy notice. The next cheapest — delete the switch — is a legitimate answer and I have put it in front of you as one.

---

## Open questions

| # | Must / should / nice | Question | Owner | What it blocks |
|---|---|---|---|---|
| Q1 | **Must** | **Frontline first, or the portal as you asked?** My recommendation is frontline. | Surbhi | The whole slice |
| Q2 | **Must** | **Who is the named human who reads the Hindi**, and by when? A tenant HR person, someone at AllAboutHR, or a paid translator? | Surbhi | Any language being offered at all |
| Q3 | **Must** | **What happens to the ~75 machine-draft Hindi strings on `field-checkin.html` before `dtc` goes live** — reviewed, or switch removed? | Surbhi | The go-live, next week |
| Q4 | Should | Is Punjabi a real customer need, or anticipation? Name the customer if there is one | Surbhi | Whether Punjabi is in any plan at all |
| Q5 | Should | Does `dtc`'s workforce read Hindi, and do they use the desktop portal or a phone? | Surbhi / the client | The Kano class in section 4, and Q1 |
| Q6 | Should | May a tenant HR person edit wording on their own site later? (Wave 5's D-5 said no for v1) | Surbhi | A later slice, not this one |
| Q7 | Nice | Budget for professional translation of ~1,500 portal phrases — I need a quote, not a guess | Surbhi | Any portal option |
| ⚠ Q8 | Should | Counsel: does an inaccurate Hindi privacy notice weaken the notice? **I am not a lawyer** | Surbhi + counsel | Whether Q3's review must precede go-live |

## Assumptions

- `[ASSUMPTION]` `dtc` and the demo tenants have frontline staff who read Hindi better than English. **This is the load-bearing assumption of the whole brief and it is unverified.** Q5 closes it.
- `[ASSUMPTION]` Managers and HR users in our tenants work comfortably in English.
- `[ASSUMPTION]` The browser check-in page is still reachable by real workers alongside the installed field app. If it is fully retired, R3 shrinks and Q3's answer becomes "remove the switch".
- `[ASSUMPTION]` Wave 5's server-side code ports to the old frame with the switch control and string wrapping as the only frame-specific work. Read from its documents, **not re-verified against the old page** — the engineer must confirm in `00`.
- `[ASSUMPTION]` Nobody has asked for Hindi in a demo or a ticket. I found no record; absence of a record is not proof.
- **Could not check:** YouTrack **ALV-83** and **ALV-7**, including ALV-7's closing comment. I have no YouTrack access in this session and the shell was disabled. Everything I say about the discarded redesign and today's measurements comes from your message and from the repo. **If either ticket contradicts this brief, the ticket wins.**

## Kill criteria — what would make me stop

1. **No named reviewer within two weeks.** Then we are building machinery for words nobody will write. Stop, remove the machine-draft switch, ship English, revisit when a customer asks.
2. **`dtc`'s and `ppj`'s workforces turn out to read English at work.** Then Hindi is anticipation, not demand. Stop everything except R3's clean-up.
3. **Wrapping one portal screen costs more than a day.** Then the portal option is not a slice and option A is off the table until a customer pays for it.
4. **Under ~10% of a Hindi-first frontline group choose Hindi after two weeks.** Then we were wrong about the person, and nothing downstream is worth building.

## Handoff note

To the UX designer and the analyst: **do not start from Wave 5's design.** It was drawn for a frame that no longer exists, and its switch lived in a profile sheet the old portal does not have — I checked: the existing portal has no personal-settings area at all (no theme control, no profile sheet), so if the portal option is chosen, **where the switch goes is an open design problem, not a port.** Start instead from `field-checkin.html`'s existing EN/हिं control, which is a real shipped design a real worker can use, and from the three things Wave 5 paid a bench to learn: a website page gets no dictionary unless its own controller emits one; a `Translation` row overrides the catalogue on the next request; and **Frappe's Jinja does not escape, so a translation is code.** To whoever picks this up: the most valuable artifact on `slice/046-redesign-wave5` is not the feature — it is `docs/slices/046-redesign-wave5/00b-bench-findings.md`. Read it before writing a line.
