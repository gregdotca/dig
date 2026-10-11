# Changelog

## 2026-10-11

- Add `CLAUDE.md` with run, lint, and architecture notes for Claude Code, including how the untracked dev/prod switch scripts work.
- Update the copyright notices in `LICENSE` and `README.md` to `Copyright (c) 2025-2026 Greg Chetcuti <greg@chetcuti.com>`, so the years are current and the notices include a contact email.
- Build Tailwind 4.3.3 and daisyUI 5.7.42 CSS at Docker build time instead of loading them from jsDelivr. The page used the in-browser Tailwind compiler, a floating `daisyui@5` tag, and a separate themes file pinned to `5.0.0`, so every visitor downloaded and ran a third-party compiler, and upstream releases could change the styling without any change here. The build now produces a single minified `app.css` (about 26 KB, 5 KB gzipped) with only the classes the template uses and the `bumblebee` theme.
  - `services/web/Dockerfile`: the builder stage downloads the Tailwind standalone CLI (checksum-verified, amd64 and arm64) and builds the CSS; the final stage copies in `app.css`.
  - `services/web/project/styles/app.css`: new Tailwind input file.
  - `services/web/project/styles/daisyui-5.7.42.mjs`: vendored daisyUI plugin.
  - `services/web/project/templates/home.html`: load `app.css` locally instead of the three CDN files.
  - `.gitignore`: ignore the generated `project/assets/app.css`.
- Add this changelog.
