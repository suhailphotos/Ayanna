# Ayanna

Ayanna is a modular machine learning workspace combining shared utilities and individual project pipelines via Git worktrees.

## Overview

The Ayanna repository serves as the central package that aggregates common code, utilities, and interfaces for multiple machine learning subprojects, each maintained as a separate Git worktree. This structure enables:

* **Modularity**: Shared code lives in the root package. Subprojects (e.g., `imgSeg`) reside in their own directories and can use or extend the core package.
* **Isolation**: Each ML project has its own branch, dependencies, and folder structure, preventing conflicts and simplifying parallel development.
* **Versioning**: Worktrees allow each project branch to have an isolated working directory, all linked back to the single Ayanna Git repository.

## Repository Layout

```
ayanna/                  # root clone of the repository
├── data/                # shared data resources
├── docs/                # shared documentation
├── src/
│   └── ayanna/          # core utilities and modules
├── tests/               # tests for the core package
├── .gitignore
├── pyproject.toml       # defines the `ayanna` package
└── README.md            # this file

# Example subproject worktree layout (imgSeg project):
# imgSeg/               # worktree for branch `imgSeg`
# ├── README.md         # subproject-specific README
# ├── data/
# ├── docker/
# ├── notebooks/
# ├── src/imgseg/
# └── ...
```

## Getting Started (Root)

### 1. Clone the repository

```bash
git clone git@github.com:suhailece/ayanna.git
cd ayanna
```

### 2. Install core dependencies

Using Poetry:

```bash
poetry install
```

Or editable install:

```bash
pip install -e .
```

### 3. Create a worktree for a subproject

```bash
git worktree add -b <projectBranch> ../<projectName> origin/main
cd ../<projectName>
```

* Replace `<projectBranch>` with the branch name (e.g., `imgSeg`).
* Replace `<projectName>` with the directory name (e.g., `imgSeg`).
* Set up the subproject folder structure and install its dependencies.

### 4. Develop

* **Core**: Make changes in `src/ayanna/` on the `main` branch.
* **Subproject**: Switch to the worktree directory, develop on its branch, and commit changes there.

### 5. Publish

* **Core Package**: bump version in `pyproject.toml`, then:

  ```bash
  poetry build && poetry publish
  ```
* **Subprojects**: Package or Dockerize as needed within their worktree.

---
