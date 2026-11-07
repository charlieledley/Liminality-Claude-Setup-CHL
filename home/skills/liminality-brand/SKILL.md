---
name: liminality-brand
description: Apply the Liminality Capital design system whenever a deck, slide, Word document, chart, table image, email signature or other visual output is produced or restyled in any repo or session. Loads the current style guide and token file from C:\Liminality-Design-Kit and the role rules that are easy to get wrong (cobalt is the logo blue, never analytical; charts restrained, principal series by weight and label in ink, bright blue only when emphasis is warranted; red only for losses, nothing green; map by role, never by old name). Use before choosing any colour, font or layout, when migrating an existing document onto the system, and when briefing a reviewer on a design change.
---

# Liminality brand

The identity lives in `C:\Liminality-Design-Kit`. Nothing here is a restatement; this skill
tells you what to open and in what order, and what to check before output goes out.

## 1. Open these first, every time

1. `C:\Liminality-Design-Kit\docs\style-guide.md`, sections 1 and 2 before any colour
   decision, section 5 before any chart, section 4 before any slide layout, section 7 for
   documents and cards. Cite the section when you apply a rule.
2. `C:\Liminality-Design-Kit\tokens\liminality-tokens.json` for the exact values. The
   `role` strings there are summaries; the guide is the authority.
3. `C:\Liminality-Design-Kit\docs\decisions\` for why a value is what it is. Decisions are
   append-only; do not re-open one in chat, propose a new decision file.

## 2. The rules that have been broken before

- Cobalt `#0047BB` is the signature logo blue: the logo and signature marks only. Never a
  chart series, bullet, band or highlight; never on an analytical page.
- Charts are restrained by default: the principal series is the heaviest line, in ink,
  labelled at its end; comparators blue-gray, silver, muted violet. Bright blue `#2F6ED3`
  only when emphasis is warranted, one element per page, most pages none.
- Red `#B3332E` only for losses in signed figures and loss tiles; mixed-sign cells ink.
  Nothing is green: the positive green was removed on 2026-10-18.
- The exceptional tier (electric blue `#1259DD`, electric violet `#3E1FF9`, vermilion
  `#F04B32`) perhaps one page in ten, never small text, never beside the negative red.
- Hyperlinks indigo, underlined.
- Deep ink `#11142E` is the dark; midnight `#011C40` is retired; gold is excluded.
- Garamond titles, Calibri text; chart pictures in Carlito (matplotlib drops Calibri text).
- Map by role, never by old name, when restyling an existing document: list every coloured
  element and its role (title, body, panel, principal series, comparator, context,
  emphasis, gain, loss) before assigning colours.

## 3. Reusable pieces

- Python design module: `C:\Liminality-Design-Kit\module\liminality_brand.py` (generated;
  copy it into the repo's deck folder, never edit the copy). Constants: INK, INDIGO,
  BLUE_GRAY, SILVER, MIST, PAPER, SIGNATURE (cobalt, logo only), BRIGHT (warranted
  emphasis), ELECTRIC_BLUE, ELECTRIC_VIOLET, VERMILION, NEGATIVE, VIOLET_MUTED,
  SERIES_ON_WHITE, OFFICE_THEME, DISPLAY_FONT, TEXT_FONT, CHART_FONT, geometry, `rgb()`
  for python-pptx. ACCENT and HIGHLIGHT remain as compatibility aliases.
- matplotlib style: `C:\Liminality-Design-Kit\tokens\derived\liminality.mplstyle`.
- CSS variables: `tokens\derived\liminality.css`. Office colour scheme fragment:
  `tokens\derived\office-clrScheme.xml`.
- Logo files: `C:\Liminality-Design-Kit\logo\` (README says which file where).
- A worked migration with its review: `C:\Liminality-put-writing-strategy\docs\deck-design-v2-2026-10-17.md`
  and that repo's `recovered/session-2026-09-21/deck/dsl.py`, `brand_check.py`.

## 4. Before anything goes out

1. Run a brand check on the saved file (retired colours, non-brand typefaces, theme slots,
   no cobalt on analytical pages, at most one bright-blue element per page, no exceptional
   colour beside the negative red).
2. Run the geometry QA and open the file in the real application (PowerPoint or Word).
3. Look at every rendered picture for missing text.
4. Confirm the data files the document reads are byte-identical before and after, or route
   the change through the content review.
5. For an investor deliverable, an independent review by a different agent, briefed with
   the style guide itself, not a summary.

## 5. Changing the system

Values change in the token file, with a decision file, then `scripts/build_tokens.py` and
`scripts/build_module.py` in the kit, then recopy the module into any repo that carries it.
Update `docs/style-guide.md` in the same change; the guide and the tokens carry the same
version number.
