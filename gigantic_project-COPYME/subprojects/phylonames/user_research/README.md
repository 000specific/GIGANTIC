# User Research - phylonames

**Your personal workspace for phylonames-related work.**

---

## Where to Put Your Work

GIGANTIC gives you flexibility in organizing your research. You can use:

### Option 1: Here (`user_research/`)
Keep work close to the subproject it relates to.

```
subprojects/phylonames/user_research/
├── notes/
├── exploratory_scripts/
├── literature/
└── [your organization]
```

### Option 2: Research Notebook (`research_notebook/research_user/`)
Keep all your personal work in one central location.

```
research_notebook/research_user/subproject-phylonames/
├── notes/
├── exploratory_scripts/
├── literature/
└── [your organization]
```

### Option 3: Both
Use `user_research/` for active work, then move completed work to the research notebook.

---

## What Goes Here

- Personal notes and documentation
- Exploratory scripts and analyses
- Literature references
- Draft figures
- Quality checks
- Meeting notes
- Anything related to this subproject

---

## What Does NOT Go Here

- **Workflow inputs** - Use `nf_workflow-*/INPUT_user/` (structured formats)
- **Workflow outputs** - Generated in `nf_workflow-*/output/`
- **Inter-subproject data** - Goes to `output_to_input/`

---

## Post-Workflow Cleanup

When archiving a completed project, you may want to consolidate:
- Move `user_research/` contents to `research_notebook/research_user/subproject-phylonames/`
- This keeps all user research in one place for the scientific record

---

## Freedom of Organization

**There are no rules here.** Organize however works for you.
