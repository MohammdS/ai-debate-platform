# Product Requirements Document (PRD) - AI Debate Platform

## 1. Project Overview
The AI Debate Platform is a Python-based tool designed to facilitate structured, competitive debates between two AI models, moderated and judged by a third AI model. The goal is to create an engaging and intellectually stimulating debate environment where models defend their assigned positions vigorously.

## 2. Objectives
- Provide a robust framework for AI-driven debates.
- Ensure debaters are persistent and competitive.
- Deliver a clear verdict and scoring from a neutral judge.
- Adhere to professional software engineering standards and guidelines.

## 3. Key Features
### 3.1 AI Roles
- **Debater A:** Prompted to defend a specific topic or stance.
- **Debater B:** Prompted to defend the opposing topic or stance.
- **Judge:** Prompted to moderate the debate, evaluate arguments, and declare a winner based on predefined criteria (logic, evidence, persuasion, etc.).

### 3.2 Debate Structure
- Total of 20 messages in the debate.
- Each debater contributes 10 messages.
- Alternating turns (A -> B -> A -> B ...).
- The judge provides a final summary, scores for each debater, and a winner declaration.

### 3.3 Competitive Behavior
- Debaters must "stand up for their idea" and not concede easily.
- Both debaters seek to win the debate at all costs.
- High-intensity, high-quality argumentation.

## 4. Technical Requirements
- **Language:** Python 3.10+.
- **AI Integration:** Support for major AI models (e.g., OpenAI, Anthropic, or local models via a standard API).
- **Guidelines Compliance:**
    - Max 150 lines of code per file.
    - Modular architecture (SDK-based).
    - OOP principles.
    - TDD (Test Driven Development) with >85% coverage.
    - `uv` for package management.
    - Ruff for linting.
    - Proper error handling and logging.

## 5. User Interface
- Initial version: CLI-based for configuration and debate execution.
- Configurable topics and model parameters via JSON files.

## 6. Success Criteria
- Successful execution of a 20-message debate.
- Clear and logical judging output.
- All code passing linting and tests.
- Full compliance with `software_submission_guidelines-V3.pdf`.
