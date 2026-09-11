---
name: minimax-image-gen
description: Use when generating images with MiniMax image-01.
required_environment_variables:
  - name: MINIMAX_API_KEY
    prompt: MiniMax image-01 API key
    required_for: full functionality
---

# MiniMax Image Generation Skill

Generate text-to-image requests with MiniMax `image-01` through the bundled
standard-library helper. It supports one public character reference, but not
local-reference upload, masking, or general image editing.

## When to Use

- The user explicitly asks to generate an image with MiniMax or `image-01`.
- The user needs character-consistent generation from one public HTTPS reference image.
- Don't use for unrequested paid test calls, masked editing, or a local reference upload.

## Prerequisites

- `MINIMAX_API_KEY` is present in the execution environment. Ask the user to
  configure it if it is absent; never request it in chat or put it in commands
  or files.
- Resolve `scripts/generate.py` relative to this skill directory before
  invoking it.
- Choose a user-facing output directory and create it through the helper's
  `--output-dir` argument.

## How to Run

First inspect supported options through Hermes `terminal`:

```text
terminal(command="python3 <skill-dir>/scripts/generate.py --help", timeout=180)
```

For a normal request, invoke the helper through `terminal`:

```text
terminal(command="python3 <skill-dir>/scripts/generate.py --prompt 'A ceramic fox in soft morning light' --aspect-ratio 4:3 --output-dir outputs", timeout=240)
```

Use `--prompt-file` with a UTF-8 file for long prompts. Default to one image.
`--width` and `--height` replace `--aspect-ratio`; both dimensions are required.
Use `--reference-url` only with one user-provided public HTTPS
character-reference URL.

## Procedure

1. Confirm the user requested generation and determine the prompt, output
   directory, and whether a character reference is user-provided. **Complete
   when no paid request will be made beyond the user's stated scope.**
2. Check that `MINIMAX_API_KEY` is available without exposing its value.
   **Complete when the key is present or the user has been asked to configure
   it.**
3. Run the helper once with the selected options. **Complete when it returns
   JSON paths, a partial-result report, or a clear API/transport failure.**
4. For every returned path, inspect the saved image with `vision_analyze`.
   **Complete when each generated image has been checked for material
   mismatch.**
5. Report the absolute paths, count received versus requested, any
   safety-blocked partial result, and material mismatch. In the TUI, paths do
   not render inline; state the paths plainly. **Complete when every saved image
   is accounted for.**

## Pitfalls

- Each request may incur charges. A timeout or transport failure has unknown
  generation and charge status; do not automatically retry.
- API failures include a status code, status message, and trace ID when MiniMax
  returns them. Resolve authentication, quota, rate-limit, or invalid-input
  causes before resubmitting.
- Base64 output is saved locally; no expiring hosted URL is needed.
- A response can be partial when MiniMax blocks some images for content safety.
  The helper reports any paths already saved and exits with status 2.
- Do not claim a live generation test when only offline validation ran.

## Verification

- The helper prints JSON with absolute `paths`, `requested`, `received`, and
  `partial` fields after a successful or partial request.
- Inspect every listed output with `vision_analyze` before describing it to the
  user.
- API reference: [Text-to-Image](https://platform.minimax.io/docs/api-reference/image-generation-t2i)
  and [generation guide](https://platform.minimax.io/docs/guides/image-generation).
