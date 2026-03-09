## Roadmap To Move Closer To DivorceMate

### Priority 0: Scenario Parity Harness

- Define a canonical scenario model with explicit fields for guideline income, actual income, spousal-only income, overrides, claimant assumptions, custody type, and relationship facts.
- Add golden fixtures for the lawyer-provided scenario and additional benchmark scenarios.
- Assert key line items in tests: child support, offset, taxes, payroll deductions, benefits, NDI, SSAG low/mid/high, and duration.

### Priority 1: Tax Engine Fidelity

- Replace the simplified tax-only engine with a detailed family-law tax engine.
- Model actual income tax, payroll deductions, common non-refundable credits, and the after-tax effect of support.
- Separate tax outputs into components that can be shown in the report and reused by the NDI engine.
- Use actual year-specific values where available and only extrapolate when source data is missing.

### Priority 2: Child Support Modernization

- Add versioned child-support tables by year.
- Support over-$150,000 discretionary handling and explicit user-entered child-support overrides.
- Expand beyond a simple offset model for sole, shared, and split custody.
- Add section 7 special-expense inputs and apportionment.

### Priority 3: Real SSAG Engine

- Replace the current target-band solver with SSAG formula implementations.
- Support with-child and without-child formulas, low/mid/high ranges, duration, ceilings, floors, restructuring, and exception flags.
- Keep overrides explicit and separate from formula outputs.

### Priority 4: Benefits And Household Logic

- Model household composition and claimant allocation directly.
- Distinguish tax credits from transfer benefits.
- Make shared-custody allocations configurable rather than blanket 50/50.

### Priority 5: Reporting And Auditability

- Show taxes, payroll deductions, credits, overrides, SSAG ranges, chosen support level, duration, and assumptions separately.
- Add a calculation trace payload for debugging and regression review.

### Priority 6: Validation Matrix

- Build a benchmark suite across custody types, income ranges, and provinces.
- Add tolerance-based regression tests and report snapshots.
- Run the full test suite on every increment.

## Current Execution Order

1. Complete Priority 1.
2. Re-run the lawyer comparison scenario and quantify the remaining variance.
3. Start Priority 2 once the tax engine is stable.
