# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`dig` is a small Flask web front end for DNS lookups (demo: https://dig.greg.ca). It's a single-module app: all routes and logic live in `services/web/project/__init__.py`, and the only template is `services/web/project/templates/home.html`.

## Running

Production (the committed config): gunicorn on container port 5000, published on host port 8091.

```sh
docker-compose up -d --build
```

Development uses untracked files listed in `.git/info/exclude` (`docker-compose.DEV.yml`, `services/web/Dockerfile.DEV`, `to-dev.sh`, `to-prod.sh`, and `test.py`). `to-dev.sh` and `to-prod.sh` swap environments by **renaming files**: the active environment's files are always `docker-compose.yml` and `services/web/Dockerfile`, and the inactive ones carry a `.PROD`/`.DEV` suffix. The committed `docker-compose.yml` and `Dockerfile` are the production versions, so check which environment is active (`ls docker-compose.*.yml`) before editing or committing either one. The dev setup runs `python manage.py --debug run -h 0.0.0.0` on port 5000 with `services/web/` mounted into the container, so code changes reload live. Alongside it, `tailwindcss --watch=always` rebuilds `project/assets/app.css` into the mounted directory.

Without Docker (needs the `dig` binary from dnsutils/bind-tools on the host, since pydig shells out to it, and the Tailwind standalone CLI to build the CSS):

```sh
cd services/web
tailwindcss -i project/styles/app.css -o project/assets/app.css --watch &
FLASK_APP=project/__init__.py flask --debug run
```

## Lint and Tests

There's no test suite. Lint runs inside the production Docker build (builder stage) and fails the build on errors, so match it locally:

```sh
cd services/web && flake8 --ignore=E501,W503,F401 .
```

The root `test.py` is an untracked scratch script, not a test.

## Architecture

- **URL scheme is the state.** `POST /` reads the form (`address`, `record_type`, `server`), fills in defaults (`example.com`, `A`), and redirects to `/<address>/<record_type>[/<server>]`. `GET /` redirects to `/example.com/A`. Lookups only happen on those GET routes, so every result is a shareable URL.
- **Lookup** (`run_dig`) uses `pydig`, which runs the system `dig` binary; that's why both Dockerfiles install `dnsutils`. With a server segment it uses `pydig.Resolver(nameservers=[...])`. pydig passes the address to `dig` as its own argument, so `run_dig` rejects addresses starting with `-` or `+` (`"Error: Invalid address"`); otherwise `dig` would read them as options such as `-f<file>`. The record type is safe because pydig only accepts its known types, and the server is prefixed with `@`. Any exception becomes the string `"Error: Unable to get dig results"`.
- **Rendering:** `run_dig` returns either a list of answer lines or an error string. `home.html` handles both (iterates a list, otherwise prints the string). Output is autoescaped: never add `|safe`, because DNS answers (TXT records especially) are controlled by whoever owns the domain and can contain HTML.
- **Front end:** Tailwind 4 and DaisyUI 5 are built at Docker build time, not loaded from a CDN. The Tailwind standalone CLI (version and per-architecture SHA-256s pinned as `ARG`s in the Dockerfile builder stage) compiles `project/styles/app.css` into `project/assets/app.css` (gitignored), scanning only `project/templates/`. DaisyUI is the vendored plugin `project/styles/daisyui-<version>.mjs`, with only the `bumblebee` (light) and `business` (dark) themes enabled. To upgrade either one, update the Dockerfile `ARG`s (and `Dockerfile.DEV`), or replace the `.mjs` file and its reference in `app.css`. A class used only from Python or JS won't be in the build unless it also appears in a template.
- **Dark mode:** automatic only, with no toggle, JavaScript, or `data-theme` attribute. `bumblebee --default, business --prefersdark` in `project/styles/app.css` puts `business` inside `@media (prefers-color-scheme: dark)` on `:root:not([data-theme])`, so adding `data-theme` to `<html>` would lock the page to one theme. A `color-scheme` meta tag in `home.html` tells the browser about both modes before the CSS loads. Use daisyUI theme colours (`base-content`, `base-200`, and so on), not hard-coded colour classes (`text-gray-*`, `bg-white`), so both modes keep working. Tailwind's `dark:` variant uses the same media query, so per-mode tweaks go there (the Lookup button is `btn-accent dark:btn-primary`). Dark-mode overrides of theme variables live in an unlayered rule at the end of `project/styles/app.css`: a darker `--color-primary` for the button, and `bumblebee`'s `--radius-*` corner sizes so both modes match. Being unlayered, it beats daisyUI's layered theme.
- **Static files** are served from `project/assets/` at `/assets/...` (Flask's `static_folder`; use `url_for('static', ...)`). jQuery and the favicon are vendored there. The loading spinner is shown by an inline `onclick` on the submit button.
- **`custom.headers`:** `home.html` does `{% include 'custom.headers' ignore missing %}` in `<head>`. The file is gitignored and holds deployment-specific head content (such as analytics), so the app works without it.
- `manage.py` wraps the app in a `FlaskGroup`; gunicorn serves `manage:app`.
