---
rating: B3b
spec: "0.1"
updated: 2026-10-11
---

# AI Code Rating

**ACR B3b** (Maintainer: Experienced · AI Share: 51–75% · Oversight: Reviewed)

This project is rated with [AI Code Rating](https://aicoderating.com/spec/0.1/), spec version 0.1.

## How AI Was Used

The maintainer wrote dig by hand in 2025: the Flask app, the DNS lookups, the page template, and the Docker setup. In 2026 an AI coding agent added a step to the Docker build that compiles the page's CSS locally instead of loading it from a CDN, added automatic dark mode, fixed three security problems (unescaped DNS results, addresses being read as `dig` options, and an open redirect), and upgraded Python and the dependencies. It also added lookup timeouts and more gunicorn workers, blocked lookups against private DNS servers, added security headers and clearer error messages, and wrote the project's test suite. The maintainer chose the changes and the look, including the dark mode colours, and read all of the code the AI wrote.

The AI's changes are also reviewed by a second AI, and the two go back and forth until it doesn't find any more issues. That doesn't change the oversight level. Commits are marked with `Co-Authored-By: Claude Code` and, where Codex reviewed them, `Reviewed-By: Codex`.
