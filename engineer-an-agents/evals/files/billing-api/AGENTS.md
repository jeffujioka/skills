# Repository Guidelines

## Project Overview
Billing API for the Acme invoicing service.

## Stack
This is a Node.js project written in TypeScript with Express.

## Commands
- Run the tests with `npm test`.
- Run `npm run migrate -- --env=staging` before `npm run seed`. Seed fails silently on an unmigrated database.

## Conventions
- Indent with 2 spaces.
- Never edit files in `src/generated/`. Run `npm run codegen` to rebuild them.
- Write clean, readable code.
- Release procedure: bump the version in `package.json`, add a CHANGELOG.md entry, tag `vX.Y.Z`, push the tag, run `npm publish --tag next`, then promote with `npm dist-tag add billing-api@X.Y.Z latest`.
