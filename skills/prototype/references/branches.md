# Prototype branches

## LOGIC

One self-contained HTML file a non-developer can click. Isolate the reducer/machine in a pure `<script>` that does not touch the DOM; the page is a thin shell. After every action, print the full relevant state. If someone says "that shouldn't be possible", that is the finding.

Do not add tests, a bundler, a framework, or the real database.

## UI

Several *radically* different looks on one route (or sibling HTML files) with a switcher. The point is contrast, not polish. Tokens may be invented for the prototype; production still consumes designer tokens.

## FAKE

A door that looks real enough to measure intent: waitlist, "notify me", or a pricing CTA that does not charge. Record clicks as the test. Never take payment. Never persist personal data beyond a local note. This is falsify rung 5, not a launch.
