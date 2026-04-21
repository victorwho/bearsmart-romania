```markdown
# Design System Document: The Rugged Editorial

## 1. Overview & Creative North Star: "The Digital Ranger"
This design system rejects the "corporate-sanitized" look of typical data platforms. Instead, it adopts the persona of **"The Digital Ranger"**—an aesthetic that is authoritative, rugged, and deeply rooted in the natural world, yet executed with the precision of a high-end editorial field guide.

The objective is to move beyond "standard" UI. We achieve this through **Intentional Asymmetry** and **Tonal Depth**. By utilizing wide margins, overlapping map elements, and a sophisticated layering of forest-inspired tones, we create an experience that feels as reliable as a topographical map and as premium as a luxury outdoor journal. We do not use borders to define space; we use light, shadow, and environment.

---

## 2. Colors: The Earth & The Alert
Our palette is a sophisticated dialogue between deep forest pigments (`primary`) and the warm, sandy foundations of the trail (`surface`).

### The "No-Line" Rule
**Standard 1px borders are strictly prohibited for sectioning.** Boundaries must be defined solely through background color shifts.
*   **Implementation:** A `surface-container-low` (#f9f3e6) section should sit directly against a `surface` (#fff9ed) background. The change in tone is the boundary.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—stacked sheets of textured paper or frosted glass.
*   **Base:** `surface` (#fff9ed)
*   **Elevated Content:** `surface-container` (#f3ede1)
*   **Interactive Cards:** `surface-container-highest` (#e8e2d6)
*   **Nesting:** When placing a card inside a side panel, the panel should be `surface-container-low`, and the card should be `surface-container-lowest` (#ffffff) to create a "punched-out" effect.

### The "Glass & Gradient" Rule
To evoke the morning mist of the backcountry, use **Glassmorphism** for floating map controls.
*   **Floating Panels:** Apply `surface` at 80% opacity with a `backdrop-blur` of 12px.
*   **Signature Textures:** Use a subtle linear gradient for primary CTAs (e.g., `primary` #17341d to `primary-container` #2d4b32) to add "soul" and depth.

---

## 3. Typography: The Editorial Guide
We use a dual-font system to balance rugged character with data-driven precision.

*   **Display & Headlines (Manrope):** This is our "voice." **Manrope** provides a modern, slightly geometric feel that maintains authority. Use `display-lg` (3.5rem) with tight letter-spacing (-0.02em) for high-impact hero moments.
*   **Body & Data (Public Sans):** This is our "utility." **Public Sans** is chosen for its exceptional legibility on complex maps and dense data tables.
*   **The Hierarchy of Trust:**
    *   **Headlines:** Always `primary` (#17341d) to anchor the page.
    *   **Body:** `on-surface-variant` (#424842) for long-form reading to reduce eye strain.
    *   **Labels:** `label-md` (0.75rem) in `secondary` (#805533) for a "field note" aesthetic.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are often too "digital." We use **Ambient Depth**.

*   **The Layering Principle:** Avoid shadows for static elements. Simply stack `surface-container-highest` on `surface`.
*   **Ambient Shadows:** For floating elements (like a bear sighting report modal), use a diffused shadow: `0px 12px 32px rgba(29, 28, 20, 0.06)`. The color is a tint of our `on-surface`, never pure black.
*   **The "Ghost Border" Fallback:** If a map element requires a stroke for legibility, use the `outline-variant` (#c2c8bf) at **15% opacity**.
*   **Tactile Radius:** Use `md` (0.375rem) for functional components (inputs, buttons) and `xl` (0.75rem) for large containers to maintain a "professional but accessible" softness.

---

## 5. Components

### Buttons
*   **Primary:** Solid `primary` (#17341d) with `on-primary` text. No border. Subtle gradient on hover.
*   **Secondary:** `surface-container-highest` background with `primary` text. This feels integrated into the page.
*   **Alert (High Vis):** Use `tertiary` (#4a2400) for urgent actions, or `error` (#ba1a1a) for danger zones.

### Cards & Lists
*   **The "No-Divider" Rule:** Never use horizontal lines to separate list items. Use `2.5rem` (spacing scale `10`) of vertical whitespace or alternating background shifts between `surface-container-low` and `surface-container-highest`.
*   **Rich Data Cards:** Use `surface-container-lowest` (#ffffff) with a `4px` left-accent bar in `secondary` (#805533) to denote "Nature/Sightings" data.

### Map Legend & Chips
*   **Sighting Chips:** Use `secondary-container` (#fdc39a) for low-risk sightings and `tertiary-container` (#6a3700) for predatory alerts.
*   **Selection Chips:** Use `primary-fixed` (#c8ecc9) for active states to give a "living" green feel.

### Input Fields
*   **Style:** Minimalist. No bottom line. A subtle `surface-container-highest` fill with an `sm` (0.125rem) radius.
*   **Focus State:** A `2px` "Ghost Border" using `surface-tint` (#47664b) at 40% opacity.

---

## 6. Do’s and Don’ts

### Do:
*   **Use Asymmetry:** Place map overlays off-center to create an editorial, bespoke feel.
*   **Embrace Negative Space:** Use spacing scale `16` (4rem) between major sections to let the "nature" of the design breathe.
*   **Tint Your Greys:** Always use our earth-toned neutrals. Never use `#333333` or `#eeeeee`.

### Don’t:
*   **Don't use 1px solid lines:** This breaks the "organic" feel of the system.
*   **Don't use high-contrast shadows:** They look like software from 2015. Keep them "ambient" and "airy."
*   **Don't crowd the map:** Map labels should use `Public Sans` with `label-md` sizing and a `0.5px` letter spacing for maximum clarity.
*   **Don't use sharp corners:** Even "rugged" items need the `sm` (0.125rem) radius to feel modern and accessible.

---

## 7. Signature Pattern: The "Topographical Overlay"
To emphasize the nature-inspired theme, use the `on-primary-fixed-variant` (#2f4d34) at 5% opacity to create a subtle, repeating topographical line pattern in large empty `surface` areas or behind hero headlines. This adds a "Signature Texture" that makes the design feel custom-crafted rather than a generic template.```