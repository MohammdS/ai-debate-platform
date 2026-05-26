# Sample Debate Transcript

**Topic:** Artificial Intelligence in Higher Education
**Pro stance:** AI tools should be allowed in university exams
**Contra stance:** AI tools should be banned from university exams
**Provider A (Pro):** mock
**Provider B (Contra):** mock
**Date:** 2026-05-26

---

## Debate Transcript

### Round 1

**[Pro]:** AI tools in exams test real-world skills — graduates will use AI daily in their careers. Banning them creates an artificial, outdated assessment environment. Research from Stanford (2024) found that AI-augmented problem-solving produces 40% better outcomes than isolated reasoning alone. The question is not whether students use AI, but whether they use it effectively.

*Skills selected: EvidenceSkill, ProgressionSkill*

**[Contra]:** Rebuttal: The Stanford statistic cited is unverifiable without a specific study citation. More critically, exams exist to measure individual competence — if AI answers the question, we measure the AI, not the student. Academic integrity requires that assessment reflects what the individual knows. Introducing AI breaks this fundamental principle.

*Skills selected: RebuttalSkill, CitationSkill*

---

### Round 2

**[Pro]:** Rebuttal: The integrity argument assumes a fixed definition of "individual competence." But competence in 2026 includes knowing how to use tools effectively — just as calculators were once banned and are now standard. The OECD (2023 Education Report) documents that AI-integrated curricula improve critical thinking scores by 22%. Banning AI produces graduates unprepared for the workforce.

*Skills selected: RebuttalSkill, EvidenceSkill*

**[Contra]:** Rebuttal: Calculator analogies are false equivalence — calculators execute arithmetic, not reasoning. AI generates arguments, selects evidence, and structures essays. The cognitive work being offloaded is the learning itself. Furthermore, equity is at stake: not all students have access to the same AI tools, creating a socioeconomic advantage gap that undermines fair assessment.

*Skills selected: RebuttalSkill, EvidenceSkill, ProgressionSkill*

---

### Round 3

**[Pro]:** The equity concern is legitimate, but the solution is to standardise AI access — provide every exam candidate with the same approved tool — not to ban the technology. Societies standardised calculator access; we can do the same with AI. Institutions like MIT and ETH Zurich are already piloting AI-integrated assessments with controlled toolsets. Prohibition is not a solution; it is avoidance.

*Skills selected: RebuttalSkill, ProgressionSkill, EvidenceSkill*

**[Contra]:** Socratic challenge: If AI tools are standardised and provided equally, what exactly is the exam measuring — the student's reasoning, or the quality of the institution's AI procurement? Standardised AI access does not eliminate cognitive offloading; it universalises it. The deeper question is whether an exam that permits AI is still an exam, or merely a supervised prompt-engineering exercise.

*Skills selected: SocraticSkill, RebuttalSkill*

---

### Round 4

**[Pro]:** That framing sets up a false binary. "Prompt engineering" — crafting precise, well-reasoned instructions — is itself a cognitive skill demanding domain knowledge, critical thinking, and communication ability. An exam that rewards effective AI use assesses a richer skill set than one rewarding rote memorisation. The World Economic Forum (2025) lists AI collaboration as a top-five workforce competency for every professional sector.

*Skills selected: RebuttalSkill, EvidenceSkill, CitationSkill*

**[Contra]:** Rebuttal: WEF competency lists describe workplace skills, not assessment design principles. University exams certify foundational knowledge — the base layer upon which AI collaboration skills are later built. If that foundation is never independently assessed, employers receive graduates with certificates that certify AI access, not human expertise. This erodes the signal value of academic credentials across the entire labour market.

*Skills selected: RebuttalSkill, ProgressionSkill*

---

### Round 5

**[Pro]:** The "signal value" argument presupposes that current credentials are accurate signals. Research by Harvard (2023) shows that 67% of traditional exam performance correlates with test-taking technique rather than subject mastery. AI-integrated exams with open-ended design tasks may produce more valid signals of genuine competence than closed-book recall assessments. We should improve assessment validity, not preserve a flawed status quo.

*Skills selected: EvidenceSkill, RebuttalSkill, CitationSkill*

**[Contra]:** Transcript summary: Through five rounds, Pro argues AI exams test real-world skills and workforce readiness; Contra counters with academic integrity, equity, credential signal value, and the distinction between certification and workplace practice. Both sides agree equity matters; they diverge on whether that justifies prohibition or standardised access. Core unresolved tension: is the purpose of a university exam to certify isolated knowledge or collaborative competence?

Rebuttal: The Harvard correlation cited conflates exam quality with exam format. Poor closed-book exams can be redesigned without introducing AI — better rubrics, project-based assessment, oral examinations. Pro conflates "current exams are flawed" with "AI solves the flaw." These are separate claims that require separate justification.

*Skills selected: SummarizationSkill, RebuttalSkill*

---

### Rounds 6–10

*(Full 20-turn transcript available after running: `make demo` or the command below)*

---

## Judge Verdict

```json
{
  "scores": {
    "pro": {
      "logic": 7,
      "evidence": 6,
      "rebuttal_quality": 8,
      "relevance": 8,
      "clarity": 8,
      "citation_quality": 5,
      "repetition_penalty": -1,
      "total": 41
    },
    "contra": {
      "logic": 8,
      "evidence": 7,
      "rebuttal_quality": 9,
      "relevance": 9,
      "clarity": 8,
      "citation_quality": 7,
      "repetition_penalty": 0,
      "total": 48
    }
  },
  "reasoning": {
    "pro": "Pro made strong opening arguments about workforce readiness and cited multiple sources. The calculator analogy was a productive framing. However, several cited statistics lacked precise attribution, and from round 6 onward the core argument was restated with diminishing novelty, triggering a repetition penalty.",
    "contra": "Contra consistently rebutted with precision — the equity angle, the credential signal argument, and the Socratic challenge in round 3 each introduced genuinely new dimensions. Citation discipline was maintained throughout. The round 5 transcript summary demonstrated meta-awareness of debate structure, which strengthened overall coherence."
  },
  "winner": "Contra"
}
```

**WINNER: Contra**

---

## Running Your Own Debate

```bash
# Mock mode (free, no API keys required)
uv run python -m src.main \
  --topic "Your topic" \
  --stance-a "Pro stance" \
  --stance-b "Contra stance" \
  --provider-a mock \
  --provider-b mock

# With real providers (requires API keys in .env)
uv run python -m src.main \
  --topic "Your topic" \
  --stance-a "Pro stance" \
  --stance-b "Contra stance" \
  --provider-a groq \
  --provider-b zai

# Results are saved automatically to results/
ls results/
```
