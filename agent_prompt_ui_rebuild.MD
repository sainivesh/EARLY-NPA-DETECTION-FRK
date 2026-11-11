# NPA Early Detection – Banking Dashboard UI/UX Improvement

## PROJECT OBJECTIVE

Act as a senior UI/UX designer, frontend developer and banking risk-dashboard specialist.

Your task is to improve the existing NPA Early Detection customer review webpage into a polished, professional, modern banking risk-monitoring dashboard.

The webpage must make three things immediately clear:

1. Which customers have been identified as having elevated future NPA risk?
2. Why has the SAS model assigned that risk?
3. What should the reviewer understand or do next?

The most important output is the **customer-level risk summary and AI-assisted explanation**. This must be the visual centrepiece of the application, not another ordinary information card.

Improve the existing application. Do not build a replacement application.

---

# PHASE 0 – PROJECT INSPECTION AND PRESERVATION

Before changing code:

1. Inspect the current project folder and existing implementation.
2. Read `web_app.py`, `templates/index.html`, associated CSS and JavaScript, `npa_assessment.py` and relevant RAG integration code.
3. Understand the existing API endpoints and JSON response structure.
4. Inspect the actual `NPA_SCORING_RESULTS.csv` schema and sample records.
5. Understand how the existing summary is generated and how policy citations are displayed.

### Strict preservation requirements

- Keep the existing Python `ThreadingHTTPServer`.
- Keep the existing Python backend.
- Keep the existing SQLite database untouched.
- Keep the existing ChromaDB collection and RAG knowledge base untouched.
- Preserve the existing LLM integration.
- Preserve the current customer assessment functionality.
- Preserve the existing API architecture wherever possible.
- Preserve all working business logic.
- Do not replace existing components unnecessarily.
- Do not delete or rename existing project files.
- Do not reset Git, delete untracked files or overwrite backups.
- Do not commit changes.

**Technology constraint:** Use the existing HTML, CSS and vanilla JavaScript implementation. Do not introduce React, Angular, Vue, Node.js, Vite or another frontend framework.

Use the smallest changes necessary to achieve the design.

---

# PHASE 1 – VISUAL DESIGN AND INFORMATION ARCHITECTURE

## 1. Overall design direction

Create a premium enterprise banking dashboard.

The visual language should communicate:

- Financial reliability.
- Credit-risk intelligence.
- Trustworthiness.
- Professional decision support.
- Clear analytical evidence.

### Colour palette

Use a restrained banking-oriented palette:

| Purpose | Suggested colour |
|---|---|
| Primary header | Deep navy `#153454` |
| Primary action | Banking blue `#216AA5` |
| Page background | `#F4F7FB` |
| Card background | `#FFFFFF` |
| Main text | `#1D2939` |
| Secondary text | `#667085` |
| Border | `#E4EAF1` |
| Critical risk | `#B42318` |
| High risk | `#C75B12` |
| Medium risk | `#B7791F` |
| Low risk | `#16836B` |

Use light tinted backgrounds for risk badges. Avoid filling entire cards with strong colours.

Do not use excessive gradients, unnecessary shadows, decorative animations or oversized icons.

## 2. Typography

The current screenshot has very small text.

Improve readability using a consistent font system:

- Prefer Inter if already available; otherwise use a system font stack.
- Main page title: approximately 24–28px.
- Main section headings: 17–19px.
- Customer summary heading: 20–24px.
- Body text: 14–16px.
- Table text: 13–14px.
- Supporting labels: at least 12px.
- Use comfortable line spacing of around 1.45–1.6.

Important model results and AI-generated explanations must be readable without zooming.

## 3. Header

Replace the vague heading `NPA customer review` with:

**Early NPA Risk Review**

Subtitle:

`SAS-powered customer risk predictions, financial indicators and evidence-based assessments.`

The header should be compact, aligned and professional.

Include a subtle status indicator showing:

- Scoring data loaded.
- Scoring run ID or last scoring timestamp.

Do not display a fake online or successful status if data loading fails.

---

# PHASE 2 – RESTRUCTURE THE PAGE

The current layout has a narrow customer panel and an extremely long sequence of equally weighted cards.

Redesign the page using the following structure.

## A. Desktop layout

Use a responsive two-column layout:

**Left panel: Customer explorer**
- Approximately 300–340px wide.
- Sticky position while scrolling the main customer details.
- Clear separation from the main workspace.
- Comfortable table row height.
- Consistent margins and padding.

**Right panel: Customer risk workspace**
- Uses remaining available width.
- Proper alignment between sections.
- Consistent maximum content width.
- Clear heading hierarchy.
- Avoid excessively wide tables.

Do not make the two columns visually crowded.

## B. Customer explorer – left panel

Improve the current left sidebar.

Header:

`Scored Customers`

Show:

`Showing X of 2,000 customers`

The count must update dynamically after applying filters.

Controls:

1. Search customer by ID.
2. Filter by model risk grade.
3. Filter by predicted NPA status.

Risk grade options:

- All Grades
- Critical
- High
- Medium
- Low

Prediction options:

- All Predictions
- Predicted NPA
- Not Predicted NPA

Search must work against customer ID and, where available, recommended action.

### Customer table

Use three columns:

| Risk Grade | Customer ID | Recommended Action |
|---|---|---|

Requirements:

- Proper column alignment.
- Consistent row spacing.
- Sticky table header.
- Clear selected-row background.
- Hover state.
- Risk-grade badge.
- Text truncation with tooltip when necessary.
- No overlapping columns.
- No horizontal scrolling at normal desktop sizes.

Selecting a customer must update the main workspace immediately.

The currently selected customer must be visually obvious.

If the main panel has a separate customer dropdown, keep it synchronized with the sidebar. There must never be conflicting customer selections.

Include a meaningful empty state when filters return no customers.

---

# PHASE 3 – MAKE THE RISK SUMMARY THE CENTREPIECE

This is the most important design requirement.

The main customer summary must receive the highest visual priority.

Do not bury the summary under customer-profile and technical information cards.

## A. Selected customer heading

Display:

`Customer 10174`

Include the selected customer's loan ID only when available.

Provide a compact scoring metadata line:

`Scored by SAS Model Studio | Run ID | Timestamp`

Do not hardcode sample customer details.

## B. Primary model risk summary

Design a prominent, visually distinctive summary panel.

It should contain:

- Model Risk Grade.
- Model Event Probability.
- Predicted NPA status.
- Recommended Action.

For example:

<escape>
Customer 10174

CRITICAL RISK

98.56% model-estimated NPA probability

Predicted NPA event within the next 6 months: YES

Recommended Action: RECOVERY TEAM
</escape>

Use a clear visual hierarchy:

- Probability should be the most prominent numerical value.
- Risk grade should have a strong but tasteful badge.
- Recommended action should be immediately visible.
- Prediction status should be unambiguous.

A horizontal probability indicator or compact progress bar is acceptable.

Do not create a fake gauge or visual metric with values different from the underlying data.

### Important terminology

These customers are currently performing at the scoring observation date. The model estimates their likelihood of reaching NPA in the future.

Therefore:

- Do not describe a model prediction as an existing NPA event.
- Do not describe a flagged customer as already defaulted.
- Use `Predicted future NPA risk`.
- Use the correct six-month prediction horizon from the project design.
- Explain that probability is a model estimate, not certainty.

Use the same probability value and formatting everywhere. For example, display `98.56%` consistently instead of switching between `98.56%`, `0.99` and other rounded formats.

The frontend must only format SAS probabilities. It must not recalculate them.

## C. AI-assisted executive summary

Put the AI-generated customer assessment directly underneath the primary risk summary.

Use the heading:

**Customer Risk Assessment**

Make this the most visually prominent narrative section.

The AI explanation should clearly answer:

1. Why did the SAS model identify this customer?
2. What are the most important risk indicators?
3. What historical repayment concerns are available?
4. What does the customer's current financial position indicate?
5. What action does the system recommend?
6. Which bank-policy references support the explanation?

### Summary writing requirements

- Use simple professional banking language.
- Avoid excessively technical explanations.
- Use short paragraphs.
- Highlight important financial figures.
- Distinguish historical events from current customer status.
- Distinguish model predictions from rule-based flags.
- Do not make unsupported claims about a customer's repayment behaviour.
- Do not claim that a bank policy mandates an action unless the retrieved policy supports it.

Make the summary readable rather than displaying a dense wall of text.

---

# PHASE 4 – ORGANISE THE REMAINING SECTIONS

Do not keep every section as an independent, equally styled card.

Introduce meaningful navigation within the main workspace.

Use four clear tabs or segmented navigation items:

1. Overview
2. Risk Drivers
3. Customer & Repayment
4. Policies & Evidence

The overview and customer risk summary must be visible by default.

Switching tabs must show the associated information without losing the selected customer.

Use subtle active states, smooth transitions and keyboard-accessible navigation.

### TAB 1 – Overview

Include:

- Main model risk summary.
- AI-assisted executive summary.
- Model probability and recommended action.
- A compact customer financial snapshot.
- A short list of the strongest risk indicators.

Do not duplicate the entire customer profile here.

### TAB 2 – Risk Drivers

Combine the existing:

- Primary Risk Factors.
- Secondary Risk Factors.
- Additional Risk Indicators.
- Active Internal Risk Flags.

Use one organised risk-driver presentation.

Show a table with:

| Risk Indicator | Observed Value | Rule Threshold | Explanation | Evidence |
|---|---|---|---|---|

Requirements:

- Sort the strongest or most relevant indicators first.
- Highlight active risk indicators.
- Clearly distinguish model predictors from rule-based flags.
- Use labels that match the actual data definitions.
- Do not display thresholds that are unavailable.
- Do not fabricate explanations.

### Very important: two different risk grades

The application has two separate grading systems:

**Model Risk Grade**
- Generated from the SAS champion model probability.
- LOW, MEDIUM, HIGH or CRITICAL.

**Internal Rule-Based Grade**
- Generated from the SAS business-rule flags.
- Represents an internal prototype flag count/grade.

Never combine these two grades.

Label the second as:

`Internal Rule-Based Risk Grade (Prototype)`

Keep the SAS Model Risk Grade visually dominant.

### TAB 3 – Customer & Repayment

Group information into logical subsections.

**Customer Profile**
- Customer ID.
- Age.
- Gender.
- Occupation.
- Marital status.
- Employment years.
- City type.
- Monthly income.

**Current Loan**
- Loan type.
- Sanctioned amount.
- Outstanding amount.
- Monthly EMI.
- Interest rate.
- Collateral value.
- Loan age.
- Remaining tenure.

**Credit & Financial Position**
- Credit score.
- Credit limit and balance.
- Credit utilization.
- EMI-to-income ratio.
- Outstanding ratio.
- Loan-to-value ratio.
- Other available financial indicators.

**Previous Loan History**
- History availability.
- Previous NPA events.
- Prior missed payment count.
- Average and maximum prior DPD.
- Longest consecutive missed-payment period.
- Previous repayment pattern.
- Resolution status, when available.

Do not present historical previous-loan delinquency as current-loan delinquency.

If monthly repayment details are not available in the scored CSV, state that the monthly schedule is not included and show the available historical summary.

Do not invent monthly repayments or DPD values.

### TAB 4 – Policies & Evidence

Organise:

1. Applicable bank policies.
2. Recommended action and its explanation.
3. Supporting policy citations.
4. Source references.

Remove duplicated policy references where the same reference is repeated.

Use clear policy title, policy ID and a short relevant explanation.

Make citation references expandable or clickable where the existing implementation supports it.

The AI recommendation must remain separate from the actual SAS score.

---

# PHASE 5 – MEANINGFUL FUNCTIONALITY

Every visible interactive component must perform a useful action.

## 1. Search

- Search by customer ID.
- Update results as the user types, with a small debounce.
- Clear button resets the search.
- Show a no-results message.

## 2. Risk-grade filter

Selecting CRITICAL must show only critical-risk customers.

The customer count must update immediately.

## 3. Prediction filter

Allow filtering by predicted class.

Class 1 = Predicted future NPA event.

Class 0 = No predicted future NPA event.

Use clear end-user wording.

## 4. Customer selection

When a customer is selected:

- Synchronise the sidebar and customer dropdown.
- Update model probability.
- Update predicted status.
- Update model risk grade.
- Update financial profile.
- Update active flags.
- Update risk reasons.
- Ensure the assessment belongs to the selected customer.

Never display a previous customer's assessment under a newly selected customer.

## 5. Generate assessment button

The button must call the existing POST `/api/summary` endpoint.

Implement:

- Disabled state while processing.
- Loading spinner.
- Button label change to `Generating assessment...`.
- Proper response handling.
- Error state.
- Retry action.
- Success state.

Prevent multiple simultaneous requests for the same customer.

Do not regenerate the assessment unnecessarily when switching between unrelated sections.

---

# PHASE 6 – LOADING, SCROLLING AND RESPONSIVENESS

## 1. Loading animations

Make page loading and AI generation feel smooth.

Use:
- Subtle skeleton placeholders during initial data loading.
- Small spinner inside the Generate Assessment button.
- Smooth appearance of the result panel.
- Disabled controls during relevant operations.
- Clear error and retry messages.

Do not use fake percentage progress bars or fake loading completion.

Respect `prefers-reduced-motion`.

Avoid layout jumps when content loads.

## 2. Scrolling

The existing page is excessively long.

Improve it through content grouping and navigation.

Requirements:

- Compact header.
- Sticky customer sidebar on desktop.
- Sticky section navigation where appropriate.
- Consistent card spacing.
- Main workspace should have one predictable vertical scrolling experience.
- The customer table may have its own bounded scroll area when necessary.
- Avoid multiple nested scrolling containers.
- Avoid unnecessary horizontal scrolling.
- On smaller screens, allow the sidebar to collapse into a customer-selection panel.

## 3. Responsive design

Desktop:
- Two-column layout.
- Sidebar and customer detail area.

Tablet:
- Reduced sidebar width.
- Flexible KPI cards.

Mobile:
- Single-column layout.
- Collapsible customer explorer.
- Full-width summary.
- Stacked KPI cards.
- Responsive risk tables.

Do not allow text, badges, buttons or cards to overflow.

---

# PHASE 7 – DATA INTEGRITY AND BANKING TERMINOLOGY

The scoring file remains the authoritative source of live predictions.

Use the actual `NPA_SCORING_RESULTS.csv` columns.

Expected fields include:

- `customer_id`
- `model_event_probability`
- `model_predicted_class`
- `model_risk_grade`
- `recommended_action`
- `internal_risk_flag_count`
- `internal_rule_risk_grade`
- `risk_reason_1`
- `risk_reason_2`
- `risk_reason_3`

Use additional customer and loan attributes only when they exist in the actual CSV.

### Strict data rules

1. Validate the CSV before using it.
2. Expect 2,000 separate live scoring customers.
3. Verify unique customer IDs.
4. Reject missing or invalid probabilities.
5. Verify probability is between 0 and 1.
6. Verify model risk-grade values against the SAS-defined probability bands.
7. Do not replace missing values with invented customer information.
8. Do not infer a real NPA status from a model prediction.
9. Do not use the 3,000-row test dataset to populate live customer records.
10. Do not use training datasets or future simulation records to create live customer summaries.

The database must remain untouched.

The existing RAG pipeline can use customer information from the scoring CSV and retrieve policy knowledge from its existing ChromaDB collection.

### Terminology improvement

Use plain professional terms:

| Current/technical wording | Preferred display wording |
|---|---|
| `model_event_probability` | Model-estimated NPA probability |
| `model_predicted_class` | Predicted NPA outcome |
| `internal_risk_flag_count` | Active internal risk indicators |
| `internal_rule_risk_grade` | Internal Rule-Based Risk Grade |
| `prior_max_dpd` | Maximum DPD in Previous Loan |
| `prior_avg_dpd` | Average DPD in Previous Loan |
| `flag_previous_npa` | Previous NPA Event |
| `flag_history_unavailable` | Previous Loan History Unavailable |
| `recommended_action` | Recommended Next Action |

Use accurate display names for financial ratios. In particular, do not describe a general cash-outflow-to-income proxy as a formal regulatory debt-to-income measure. Use its documented source definition.

---

# PHASE 8 – TESTING AND VERIFICATION

Do not finish after changing HTML and CSS.

Run the existing application and verify the complete workflow.

## A. Backend tests

- Scoring CSV loads successfully.
- Exactly 2,000 unique customers are available.
- No duplicate customer IDs.
- No live customer is sourced from the independent test population.
- API `/api/customers` returns the correct records.
- Risk-grade filtering works.
- Predicted-class filtering works.
- Search works.
- API `/api/summary` retrieves the correct customer's scoring attributes.
- RAG retrieval works.
- LLM assessment works.
- Citations remain available.
- Invalid customer IDs return appropriate errors.

## B. Data consistency tests

For randomly selected customers, compare the webpage with the original scoring CSV.

Confirm exact consistency for:

- Customer ID.
- Probability.
- Predicted class.
- Model risk grade.
- Recommended action.
- Internal flags.
- Internal rule grade.
- Risk reasons.

The frontend may format values but must not change them.

## C. UI interaction tests

Test the following:

- Search a customer.
- Filter CRITICAL customers.
- Filter HIGH customers.
- Change predicted NPA filter.
- Select a customer from the sidebar.
- Select a customer from the dropdown, if retained.
- Generate an assessment.
- Switch between tabs.
- Change customers while an assessment is loading.
- Retry after an API failure.
- Refresh the webpage.
- Resize the browser.
- Test a mobile-sized viewport.

## D. Visual quality tests

Verify:

- No overlapping elements.
- No text clipping.
- No unreadably small font.
- No misaligned tables.
- No inconsistent padding.
- No excessive empty space.
- No unnecessary duplicate sections.
- No excessive vertical scrolling.
- No broken buttons.
- No horizontal overflow on mobile.
- No stale customer assessment after selection changes.

## E. Preservation tests

Confirm:

- `bank_data.db` remains unchanged.
- ChromaDB collection remains unchanged.
- Existing knowledge-base files remain untouched.
- The existing API architecture is preserved.
- No new JavaScript framework or Node.js dependency has been introduced.
- Unrelated project files are unchanged.

---

# PHASE 9 – FINAL DELIVERY

After implementation, provide:

1. Summary of existing UI problems found.
2. New page layout and section structure.
3. Exact files changed.
4. Backend changes.
5. Frontend and CSS changes.
6. Functional test results.
7. Responsive design test results.
8. Data integrity test results.
9. Any remaining limitations.
10. **Full-Screen Layout – No Page Scrolling Required**

The webpage must fit within the available browser viewport at standard desktop resolutions (1366×768 and 1440×900).

- No browser-level vertical or horizontal scrollbar should be required to view the main dashboard.
- The header, customer explorer, customer risk summary and primary information must fit within the visible screen.
- Use compact spacing, intelligently sized cards, responsive grids and proper content hierarchy.
- Organise detailed information using tabs, expandable sections or collapsible panels instead of extending the page vertically.
- Keep the primary risk summary and AI-generated assessment visible without requiring the user to scroll.
- Do not hide important information or simply truncate content to achieve a no-scroll layout.
- Avoid multiple nested scrolling containers.
- Dynamically adjust spacing and component sizes for different desktop resolutions.
- Verify the layout at 1366×768, 1440×900 and 1920×1080.

**Acceptance criterion:** At standard desktop resolutions, the user must be able to access all primary dashboard functionality and understand the selected customer's risk assessment without scrolling the webpage. Mobile layouts may use natural scrolling where necessary.

Do not claim a test passed unless it was actually executed.

Do not commit changes.

## FINAL DESIGN EXPECTATION

The final experience should feel like a professional banking credit-risk review application.

A reviewer should be able to open the webpage and, within a few seconds:

- Select a customer.
- Understand their future NPA risk.
- See the SAS model's probability and risk grade.
- Read a clear explanation of why the model identified the customer.
- Understand the underlying financial and historical indicators.
- See supporting bank policies.
- Understand the recommended next action.

**Prioritise clarity, readability, evidence and decision-making over decorative design.**

The AI-assisted customer assessment must be the visual centrepiece of the page.