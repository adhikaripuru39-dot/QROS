# The QROS Engineering Manifesto

**The Fifth Founding Document** — proposed in the Founding Governance Documents and adopted at founding. This document defines how software is designed and built, complementing the Constitution (why QROS exists), the Bill of Rights and Responsibilities (what is protected and expected), and the Code of Scientific Conduct (how research is performed).

### Principle 1 — Modularity over monoliths
Systems shall be composed of small, cohesive, independently testable modules. No component should be required to understand the whole before it can be understood.

### Principle 2 — Reliability over speed
Correctness under duress is preferred to speed at the limit. Systems shall fail safely and degrade gracefully; a component that cannot fail cleanly is a liability.

### Principle 3 — Observability by default
Every delivered component shall emit meaningful, structured, auditable signals about its own behavior. Observability is a product requirement, not a diagnostic afterthought.

### Principle 4 — Automation with safeguards
Repetition and judgement-free steps shall be automated, but automation never removes human accountability for the decisions the system makes.

### Principle 5 — Maintainability as a core objective
Code that cannot be understood, tested, or maintained in the future is incomplete. Clear documentation, version retention, and reproducible builds are mandatory.

### Principle 6 — Reproducibility is non-negotiable
Every experiment, pipeline stage, and artifact must be reproducible: frozen inputs, recorded parameters, deterministic results. A result that cannot be reproduced does not exist.

### Principle 7 — Security and data protection
The security of code and the integrity of data are architectural constraints, considered at design — never bolted on afterward.

### Principle 8 — Auditability and accountability
Every change has an owner, a rationale, and a measured outcome; the system keeps an immutable record of decisions (see Article IX of the Constitution).

> Adopted together with the four founding documents under the ratified Founding Governance.