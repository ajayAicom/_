# MotionAI 30s — AI Upgrade Notes

This starter is designed to stay free by rendering locally or inside the browser.

## Current included modes

### Video

- Photo Reference Mode
- No Photo Story Mode
- Hindi / English / Hinglish language selector
- 30 sec max output
- MP4 in Python app
- WebM in Firebase browser app

### Photo

- Prompt-based AI-style poster/photo graphic generator
- Upload photo resize/crop/export
- 400×400, 1:1, 9:16, 16:9, 4:5, A4, custom px sizes
- JPG / PNG / WEBP export
- Target KB/MB compression for JPG/WEBP

## Important limitation

The included prompt-photo generator is a no-model local graphic generator. It creates polished poster-style visuals with canvas/Pillow, typography, gradients and shapes. It does not generate true photorealistic objects like a full Stable Diffusion/Flux model.

For real text-to-image or image-to-video, add an AI backend.

## Recommended real AI backend architecture

```text
Firebase Hosting / Streamlit UI
        ↓
Cloud Run or local FastAPI backend
        ↓
ComfyUI / Stable Diffusion / SDXL / Flux-style image generation
        ↓
Wan / AnimateDiff / CogVideoX for video clips
        ↓
MoviePy / FFmpeg combine + resize + compress
        ↓
Firebase Storage / local download
```

## Suggested upgrade stages

### Stage 1 — Free local image generation

- Install ComfyUI locally.
- Add SDXL or another open image model.
- Connect this app to `http://127.0.0.1:8188`.
- Prompt Photo Generator becomes real image AI.

### Stage 2 — Free local image-to-video

- Add Wan / AnimateDiff / CogVideoX workflow in ComfyUI.
- Generate 3–5 sec clips from reference photos.
- Combine clips into final 30 sec video.

### Stage 3 — Firebase production

- Keep Firebase Hosting for frontend.
- Deploy Cloud Run backend for AI/render jobs.
- Use Firebase Storage to store output files.
- Add login, user history, generation limits, admin plan later.

## Recommended UI additions later

- Google login
- User video/photo history
- Admin usage panel
- Free/paid plan limits
- Queue system for long video render
- Prompt templates for bakery, product, travel, Instagram, YouTube, app icon
- Background remover integration
- Face/photo enhancer integration

## File size notes

- JPG/WEBP can be compressed close to a KB/MB target.
- PNG is lossless; exact target size is not guaranteed.
- A very small target like 50 KB at 1080×1920 may reduce quality a lot.
- Best practical exports:
  - 400×400 DP/icon: 50–200 KB
  - 1080×1080 post: 150–800 KB
  - 1080×1920 story: 300 KB–1.5 MB
  - 1920×1080 thumbnail: 300 KB–1.5 MB
