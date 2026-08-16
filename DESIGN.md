---
name: Beat The Scam
description: Calm, plain-English UK consumer protection guidance and scam checks.
colors:
  background: "#f3f6fb"
  panel: "#ffffff"
  panel-alt: "#eff4fb"
  text: "#102033"
  muted: "#5b6878"
  line: "#dbe5ef"
  brand: "#0b1220"
  brand-raised: "#152033"
  accent: "#1d4ed8"
  accent-soft: "#e8f0ff"
  accent-ink: "#163373"
  accent-line: "#cfe0ff"
  focus: "#2563eb"
  danger: "#b91c1c"
  danger-soft: "#fff1f2"
  danger-line: "#fca5a5"
  danger-ink: "#991b1b"
  success: "#15803d"
  success-soft: "#f0fdf4"
  success-line: "#86efac"
  success-ink: "#166534"
  recovery-surface: "#fef3c7"
  recovery-line: "#fcd34d"
  recovery-ink: "#78350f"
  warning-surface: "#fffbeb"
  warning-ink: "#92400e"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(2.2rem, 4vw, 4.1rem)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.05em"
  headline:
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(1.55rem, 2vw, 2.3rem)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "0.05em"
rounded:
  surface: "26px"
  panel: "18px"
  field: "14px"
  button: "999px"
spacing:
  compact: "0.75rem"
  standard: "1rem"
  panel: "1.25rem"
  section: "3.1rem"
  hero: "4.3rem"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.panel}"
    rounded: "{rounded.button}"
    padding: "0 1rem"
    height: "46px"
  button-dark:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.panel}"
    rounded: "{rounded.button}"
    padding: "0 1rem"
    height: "46px"
  button-secondary:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.brand}"
    rounded: "{rounded.button}"
    padding: "0 1rem"
    height: "46px"
  card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.surface}"
    padding: "1.25rem"
  input-search:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "0.95rem 1rem"
---

# Design System: Beat The Scam

## Overview

**Creative North Star: "The UK Consumer Safety Briefing"**

Beat The Scam feels like a calm, well-prepared briefing rather than an alarm. It pairs dark navy areas of authority with airy blue-grey reading surfaces, letting readers orient themselves before they act. The system is intentionally familiar and plain-spoken: it needs to support people making safety decisions under pressure, not reward prolonged attention.

The interface uses generous rounded containers, clear structural borders and soft ambient lift to make complex information approachable. Strong blue is reserved for actions and links; danger red marks genuine warnings rather than adding drama. Type is compactly confident, with large, direct headings and comfortably readable body copy.

**Key Characteristics:**

- Calm, protective authority rather than fear-based urgency.
- High-clarity editorial structure for stressed, mobile-first readers.
- Softly lifted white panels against a cool paper background.
- One decisive action colour, used with restraint.

## Colors

The palette is a cool, dependable briefing palette: near-black navy carries authority, blue guides action, and pale blue-grey surfaces keep long-form information breathable.

### Primary

- **Verification Blue:** The action and link colour; use it for the clearest next step, navigable text and active controls.
- **Authority Navy:** The deep anchor for hero areas, dark buttons, the footer and high-trust callouts.

### Secondary

- **Recovery Amber:** A limited recovery-action signal, reserved for routes that help after a scam rather than general interaction.
- **Protective Red:** The warning signal for risk, error and scam-specific caution; it must retain its meaning.
- **Safe Green:** A success-state signal for checker outcomes and confirmed positive feedback.

### Neutral

- **Cool Paper:** The default page background, subtly graduated near the top of the page.
- **White Briefing Panel:** The main surface for cards, guides, inputs and navigational containers.
- **Pale Blue Wash:** The low-emphasis surface for quick answers, supporting information and tonal separation.
- **Ink:** The primary reading colour and heading anchor.
- **Quiet Slate:** Supporting copy, metadata and secondary labels.
- **Soft Rule:** Borders and dividers that establish structure without making the page feel boxed in.

**The Signal-Meaning Rule.** Blue asks the reader to act; red warns of harm; green confirms safety or completion. Do not use these colours decoratively or interchange their meanings.

## Typography

**Display Font:** Inter (with system sans-serif fallbacks)

**Body Font:** Inter (with system sans-serif fallbacks)

**Character:** A single, highly legible sans-serif family keeps the experience direct and coherent. Heavy, closely tracked headings establish certainty, while generous body leading protects comprehension under stress.

### Hierarchy

- **Display:** Used for the hero promise and prominent research headings; large, heavy, tightly tracked and short-line.
- **Headline:** Used for section-level wayfinding; large enough to reset the reader's attention without competing with the hero.
- **Title:** Used for cards, panels and local decisions; firm and compact. A panel heading takes this step even when it is semantically an `h2` — the hero rail's "Verify independently" and "Look up a scam" are top-level sections of the page but subordinate objects on it, so the same heading level deliberately carries two sizes. The one rule that must hold: a heading level never renders **smaller** than the level beneath it, or a reader navigating by heading gets a different map from one scanning by size.
- **Body:** Used for explanatory copy and guides; relaxed leading supports scanning and longer reading.
- **Label:** Used for kickers and compact control language; bold, uppercase and letter-spaced only where categorisation helps orientation.

**The Plain-Reading Rule.** Keep type functional: use hierarchy to clarify a decision or sequence, never to turn safety information into spectacle.

## Layout

The site uses a centred reading frame capped at 1180px, with a minimum side inset of 1rem. Desktop composition is grid-led: the homepage hero pairs a dominant briefing panel with a 380px verification rail; cards commonly sit in two-, three- or four-column groups; guide pages combine article content with a 330px sticky sidebar. The standard gap is 1rem to 1.25rem, and sections create breathing room through a larger vertical rhythm.

At 1100px the hero grid and article layout become a single, linear reading flow, sticky sidebars return to normal document order, card grids drop to two columns, and navigation folds into a panel menu — the full link set plus the checker action needs about 1089px against the 992px available at 1024, so it cannot survive that width. The checker action sits outside the folding panel and stays visible at every size. The advisory callout switches to the pale blue wash here, so the hero and the advice below it do not read as one continuous dark region. At 860px the newsletter begins its one-column transition, so its form remains comfortably usable. At 760px card grids and the checklist finish collapsing to one column and the hero gains a little more top clearance. At 430px the wordmark, the checker action and the menu button tighten so the header stays on one line.

**The One-Clear-Route Rule.** Every dense panel should make its primary action or verification route visually obvious before adding secondary options.

## Elevation & Depth

Depth is ambient reassurance, not structural theatre. White panels are distinguished through pale borders and one diffuse, low-contrast shadow; the page stays light and quiet even when it contains many cards. Dark hero and callout panels create tonal contrast instead of relying on heavier elevation. The sticky header uses translucent white and backdrop blur to maintain context while the reader moves through a page.

### Shadow Vocabulary

- **Ambient Panel Lift:** Used under white panels, cards, articles and table-like containers to separate them gently from the cool paper background.

**The Ambient-Reassurance Rule.** Shadows should suggest a stable surface resting above the page, never a floating control demanding attention.

## Shapes

The form language is gently curved and protective. Major surfaces use broad, 26px corners; nested information panels use slightly tighter corners; inputs and disclosures become more compact again. Buttons remain fully pill-shaped, making actions easy to recognise in a content-heavy layout. Borders are thin and cool-toned, with no hard black dividers or sharp card corners.

## Components

### Buttons

**Character:** Calm and protective; strong enough to guide a next step without feeling aggressive.

- **Shape:** Fully pill-shaped, with a consistent minimum height and bold label weight.
- **Primary:** Verification Blue with white text; use for the clearest immediate action.
- **Dark:** Authority Navy with white text; use inside light input clusters or where the primary blue would compete with surrounding action.
- **Secondary:** White with an understated cool border and Authority Navy text; use for an available but lower-priority route.
- **Recovery:** A pale amber treatment reserved for post-scam recovery.
- **Hover / Focus:** Links underline on hover; action elements retain a visible blue keyboard focus outline.

### Chips

**Character:** Compact classification, never decoration.

- **Style:** Pale blue wash, darker blue text and a fine blue border.
- **Usage:** Use for categories or concise statuses that help a reader scan a group of information.

### Cards / Containers

**Character:** Reassuring editorial panels rather than product tiles.

- **Corner Style:** Broadly rounded on major surfaces, with tighter corners for nested cards and disclosures.
- **Background:** White briefing panels on cool paper; use pale blue wash for supporting information.
- **Shadow Strategy:** One ambient panel lift plus a soft rule border.
- **Internal Padding:** A consistent panel rhythm, expanded for articles and hero content.

### Inputs / Fields

**Character:** Quiet, spacious and explicit about focus.

- **Style:** White or translucent dark-surface field, cool border, compact rounded corners and readable body-sized text.
- **Focus:** A visible blue outline with space around it; the enclosing search field also indicates focus.
- **Safety States:** Checker verdicts and safety notices use the established red, amber, green and pale-blue semantic surfaces.

### Navigation

**Character:** Steady editorial wayfinding with one highlighted utility action.

- **Desktop:** A sticky, translucent white header with compact bold links and a right-aligned blue “Check a message” action.
- **Mobile:** Links collapse into a white, bordered, softly lifted panel controlled by a clear Menu button.

### Scam Checker Verdict

**Character:** A contained, readable outcome rather than a dramatic alert.

- **Style:** A rounded message panel with semantic background, border and text treatment for scam, caution, safe and unclear outcomes.
- **Usage:** Keep the verdict at the start of the result and follow it with concrete next steps.

## Do's and Don'ts

### Do:

- **Do** preserve the cool-paper background, white briefing panels and ambient lift as the baseline reading environment.
- **Do** use Authority Navy to establish trust-bearing regions and Verification Blue for the clearest available next action.
- **Do** keep headings short, direct and visibly distinct from explanatory copy.
- **Do** maintain visible keyboard focus and mobile-first linear fallbacks for all grid-based sections.
- **Do** reserve semantic warning, recovery and success colours for their established reader-safety meanings.

### Don't:

- **Don't** use panic styling, flashing urgency, aggressive contrast or decorative warning red to manufacture attention.
- **Don't** introduce a second competing action colour or treat blue, red and green as interchangeable decoration.
- **Don't** replace the rounded, softly bordered panel language with hard-edged dashboard chrome.
- **Don't** hide essential verification routes behind hover-only, icon-only or colour-only cues.
- **Don't** let dense card grids survive unchanged on narrow screens; they must collapse to the single reading flow.
