# Release Guide

ACDL is distributed to teammates as a Python wheel, not as a source checkout.

## Build Locally

```bash
sh scripts/build.sh
```

The wheel is written to `dist/`, for example:

```text
dist/acdl-0.1.0-py3-none-any.whl
```

The build script uses only Python standard library modules, so it does not require `setuptools`, `wheel`, or `python -m build`.

## Test Before Release

```bash
python3 -m unittest discover -s tests
python3 -m venv /tmp/acdl-release-test
/tmp/acdl-release-test/bin/python -m pip install dist/acdl-0.1.0-py3-none-any.whl
/tmp/acdl-release-test/bin/acdl --help
```

## Publish With GitHub Releases

Create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The GitHub Actions workflow builds the wheel, runs tests, and attaches the wheel to the GitHub Release.

## User Install Command

After the release exists, teammates install without cloning:

```bash
python3 -m pip install --user "https://github.com/TengShao/ACDL/releases/download/v0.1.0/acdl-0.1.0-py3-none-any.whl"
```

Upgrade by installing the newer release wheel URL.

Uninstall:

```bash
python3 -m pip uninstall acdl
```
