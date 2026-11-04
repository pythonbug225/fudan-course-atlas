# Implementation plan: faculty resource index and visual refresh

## Goal

Apply the approved lightweight visual refresh to the existing single-page course atlas and add one filterable, source-linked index for engineering and medical faculty materials. Keep existing course search, GPA, grade mapping, fitness, rules, and contribution flows intact. Work only on the existing `codex/engineering-course-contributions` branch / PR #5. Do not merge to `main`.

## Tasks

1. **Data and renderer** — Add a JSON index for official program directories, course lists, and clearly labeled public course-experience reporting or teaching studies. Retain the source URL, label, date/year, verification and reuse status, and scope caveat. Render records with DOM APIs and `textContent`; accept HTTPS links only.
2. **Page integration** — Add a faculty-resources navigation entry and view, with faculty/type selectors and explanatory source-boundary text. Load the resource module before the app module, connect the view/filter state, and keep existing views intact.
3. **Visual refresh** — Add restrained styling for page hierarchy, inputs, course cards, source cards, and responsive layouts, reusing the existing palette and mobile sidebar behavior. Respect reduced-motion and visible keyboard focus behavior.
4. **Verification and delivery** — Run syntax, resource-schema, integration-presence, and whitespace checks. The approved plan requested desktop/mobile screenshots and manual navigation, but the local browser preview was blocked by the browser URL policy and local-socket restrictions; record this as an unverified item and do not fabricate screenshots. Review the complete change, then commit and push only to the already authorized PR #5 branch. Do not merge or publish production.

## Review focus

- Resource JSON is valid and each record has an HTTPS source link and clear limitations.
- Social posts, raw third-party text, AI review drafts, and unsupported claims are not introduced.
- Rendering avoids HTML injection and external-link opener risks.
- The new deferred script is available before `app.js` calls it; fetch errors do not prevent existing app initialization.
- New view and selectors are wired without breaking existing navigation or course interactions.
- CSS selectors are scoped and responsive rules do not defeat the existing mobile navigation or produce obvious overflow.
- The manual screenshot and browser interaction gap is disclosed.
