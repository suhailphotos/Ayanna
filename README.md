# Ayanna

Ayanna is a modular machine learning platform designed for scalable research, clean reproducibility, and robust deployment. It combines shared utilities with independent, production-ready machine learning projects—each developed in its own Git worktree branch.

## Objective

* Provide a **plug-and-play workspace** for modern ML research and deployment.
* Enable each subproject (e.g., `imgSeg`) to evolve independently and be published under a shared Ayanna namespace (`ayanna.imgseg`, `ayanna.foo`, etc).
* Make it easy to add, develop, and maintain a family of ML models/services without dependency hell.

## Why Worktrees?

Worktrees allow you to:

* Develop each ML project in its own branch and directory, with totally separate dependencies, notebooks, Docker setups, etc.
* Merge or publish only the stable parts (e.g., via the `main` branch) while letting experimental code live in its own worktree.
* Easily add or remove subprojects as your platform evolves.

## Repository Structure

```
ayanna/                  # main clone of Ayanna
├── data/                # shared data resources
├── docs/                # shared documentation
├── src/
│   └── ayanna/          # core utilities and shared modules
├── tests/               # core/test suite
├── .gitignore
├── pyproject.toml       # defines the ayanna root package
└── README.md            # this file

# Example: subproject worktree layout (imgSeg)
imgSeg/                  # checked out as its own worktree/branch
├── README.md
├── data/
├── docker/
├── notebooks/
├── src/imgseg/
└── ...
```

---

## Getting Started: Worktree Workflow

### 1. Clone the Root Repository

```bash
git clone git@github.com:suhailece/ayanna.git
cd ayanna
```

### 2. Install Core Dependencies

```bash
poetry install
# or
pip install -e .
```

### 3. Create a New Worktree Branch for a Subproject

```bash
git worktree add -b <projectBranch> ../<projectName> origin/main
cd ../<projectName>
```

* Example: `git worktree add -b imgSeg ../imgSeg origin/main`
* This creates a new directory (`imgSeg/`) for a branch called `imgSeg` with its own isolated working tree.

### 4. Populate or Develop the Subproject

* Add or copy your ML project files, install dependencies (Poetry, Conda, Docker, etc) as needed.
* Structure and naming should match the main repo, but the codebase is independent (keeps experiments and dependencies clean).
* Example subproject namespaces: `ayanna.imgseg`, `ayanna.foo`, etc.

### 5. Commit and Push

```bash
git add .
git commit -m "Initial commit for <projectName>"
git push -u origin <projectBranch>
```

### 6. Workflow Tips

* **Core/utility changes** go in `/src/ayanna/` on the `main` branch.
* **Project-specific work** happens in its own branch/directory.
* Only stable, published code lives on the `main` branch—use it as the source of truth for production releases (e.g., for PyPI: `ayanna.imgseg`).

---

## Example: Adding Another Project

To add a new ML project called `foo`:

```bash
git worktree add -b foo ../foo origin/main
cd ../foo
# Add files, develop, commit, push as above.
```

## Cleaning Up Worktrees

```bash
git worktree remove ../imgSeg
# Optionally delete the branch (if merged)
git branch -d imgSeg
```

---

## Development Status

* **Ayanna** is under active development as a platform for plug-and-play ML projects.
* Each subproject (e.g., `imgSeg`) is expected to be modular and API-first. Future releases will standardize on a common interface.
* See subproject READMEs for usage, API endpoints, and configuration.

---

## License & Contributions

* Contributions welcome! Open issues or PRs for bugs, improvements, or new projects.

*Last updated: 2025-06-14*

