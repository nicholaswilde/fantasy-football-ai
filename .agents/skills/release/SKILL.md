---
name: release
description: Automates the versioning, tagging, and deployment process for the project by triggering GitHub Actions.
---
# /release

Automates the versioning, tagging, and deployment process for the project.

## Description
This skill handles the release process by tagging the repository with the next version and pushing the tags. This triggers the GitHub Actions workflow which automatically builds the `espn-cookie-extractor` extension zip and publishes it to GitHub Releases as a pre-release.

## Protocol

1. Determine the next version tag (e.g., `v0.1.0`, `v0.1.1`).
2. Create an annotated git tag for the release:
   ```bash
   rtk git tag <version>
   ```
3. Push the tags to the remote repository. This will automatically trigger the `.github/workflows/release.yaml` workflow to package the extension and create a pre-release in GitHub Releases.
   ```bash
   rtk git push origin main --tags
   ```
