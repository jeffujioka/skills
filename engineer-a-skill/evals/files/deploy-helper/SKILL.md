---
name: deploy-helper
description: "Deploy the current branch to the staging server. Manual-only: call it by name."
disable-model-invocation: true
---

# deploy-helper

1. Run the tests.
2. Build the image.
3. Tag the image with the commit hash.
4. Push the image to staging.
5. Check the staging health endpoint.
