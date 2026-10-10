# Contributing to ParaDecomp

We welcome contributions to ParaDecomp. To maintain publication-grade engineering standards, all contributions must strictly adhere to the following guidelines.

---

## 1. Multi-Agent Development Workflow

We operate using a multi-agent branch-and-PR workflow:

1. **Issue Creation**: File a GitHub Issue using the standard taxonomy (`feat(...)`, `fix(...)`, `docs(...)`). Provide problem statement, mathematical analysis, and acceptance criteria.
2. **Branching**: Develop strictly on topic branches off `main` (`feat/issue-<id>-...`).
3. **Automated Testing & Linter Verification**:
   - Ensure 100% test pass rate (`pytest -v`).
   - Clean linter without warnings (`ruff check src tests`).
4. **Pull Request**: Open PR referencing the issue (`Closes #<id>`). Include full summary of changes and verification proofs.
5. **Merge**: PRs are merged via fast-forward or clean merge and the branch is deleted.

---

## 2. Strict Zero-Emoji Rule

- ZERO emojis are permitted in markdown documentation, docstrings, commit messages, or terminal outputs.
- Replace status icons with formal bracketed tokens: `[PASSED]`, `[FAILED]`, `[Verified]`, `[Warning]`.

---

## 3. Architecture Diagrams

- All architecture diagrams must be rendered using GitHub-flavored Mermaid (`mermaid`) instead of ASCII box art.
- Use structured flowcharts (`flowchart TD`) and sequence diagrams with subgraphs.
