# MotionAI 30s

Free **AI-style motion graphics video + photo generator** for GitHub. It supports both video and photo workflows:

## Video workflows

1. **Photo Reference Mode** — upload reference photos and generate a motion graphics video.
2. **No Photo Story Mode** — if no photo is available, enter a topic/prompt and the app creates story scenes automatically.

## Photo workflows

1. **Prompt Photo Generator** — enter a topic/prompt and generate an AI-style poster/graphic image locally.
2. **Upload Photo Resizer** — upload a photo and export it in fixed or custom sizes.

> Important: This project is free/unlimited because rendering happens locally on your laptop/PC or in the user's browser. Paid cloud AI tools cannot be unlimited for free. This starter creates professional motion graphics, story videos, prompt-based photo graphics, resize/crop/export tools. Optional real AI image/video generation can be added later using ComfyUI + Stable Diffusion/Wan/AnimateDiff/CogVideoX if you have a strong GPU or paid backend.

## Features

### Video

- 30 sec max video duration
- Photo reference upload
- No-photo story generation
- Language selector: Hindi, English, Hinglish
- Story tone: Promotional, Cinematic, Emotional, Informative
- 1:1, 9:16, 16:9, 4:5 aspect ratio
- 720p / 1080p export
- Cinematic zoom, smooth transitions, blurred background, premium foreground card
- Captions / title overlay
- Optional logo/watermark
- Optional background music
- File name control
- MP4 download in Python local app
- WebM download in Firebase browser app

### Photo

- Prompt se AI-style graphic/photo poster
- Upload photo resize/crop/export
- 400×400 profile/app icon export
- 1:1 square export
- 9:16 story/reel export
- 16:9 YouTube thumbnail/banner export
- 4:5 Instagram portrait export
- A4 portrait/landscape 300 DPI preset in Python app
- Custom width × height in pixels
- JPG / PNG / WEBP export
- Target file size: KB or MB, best for JPG/WEBP
- File name control

## Option A: Run Python MP4 + Photo app locally

```bash
git clone https://github.com/YOUR_USERNAME/MotionAI-30s.git
cd MotionAI-30s
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Mac / Linux

```bash
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in terminal, usually:

```text
http://localhost:8501
```

## Option B: Deploy Firebase Hosting web app

Firebase static version is inside:

```text
firebase-web/
```

Deploy:

```bash
cd firebase-web
firebase login
firebase init hosting
firebase deploy
```

Firebase version runs in browser:

- Video export: **WebM**
- Photo export: **JPG / PNG / WEBP**

For MP4 video, use the Python local app or add a Cloud Run backend.

## Recommended video settings

| Use case | Aspect | Resolution | FPS |
|---|---:|---:|---:|
| Instagram Reel / YouTube Shorts | 9:16 | 720p or 1080p | 24/30 |
| YouTube video | 16:9 | 720p or 1080p | 24/30 |
| Instagram post video | 1:1 or 4:5 | 720p or 1080p | 24 |

## Recommended photo settings

| Use case | Size |
|---|---:|
| App icon / profile DP | 400×400 |
| Instagram post | 1:1 / 1080×1080 |
| Reel or Story poster | 9:16 / 1080×1920 |
| YouTube thumbnail | 16:9 / 1920×1080 |
| Instagram portrait | 4:5 / 1080×1350 |
| Print A4 | A4 300 DPI preset in Python app |

## Optional true AI upgrade

For real AI image/video generation, connect this app to a local/Cloud Run ComfyUI server and use one of these model paths:

1. **Stable Diffusion / SDXL / Flux-style image model** — real prompt-to-image generation.
2. **Wan2.2 / Wan2.1 Image-to-Video** — open image-to-video workflow, needs strong GPU.
3. **AnimateDiff + ControlNet / IPAdapter** — good for stylized motion and reference image control.
4. **CogVideoX** — open video generation family, heavier GPU requirement.

A practical workflow is:

```text
Frontend → prompt/reference image → AI backend → generated photo/clip → resize/compress/export
```

For Firebase production:

```text
Firebase Hosting → Cloud Run API → AI/video backend → Firebase Storage output URL
```

## GitHub upload

```bash
git init
git add .
git commit -m "Initial MotionAI 30s app"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/MotionAI-30s.git
git push -u origin main
```

## Notes

- 1080p rendering is slower than 720p.
- For low-end laptops, use 720p + 24 FPS.
- Python app saves generated videos/photos inside the `outputs/` folder.
- Firebase web version is backend-free and browser-based.
- Target KB/MB compression is approximate because image complexity affects final size.
- Generated outputs are ignored by git through `.gitignore`.

## License

MIT License.


UPDATE V2:
- No Photo Story Mode ab simple text-card nahi hai.
- Shimla/travel story ke liye cinematic illustrated scenes add kiye gaye: misty mountains, pine trees, Mall Road-style street, toy train, snow, evening lights.
- Instagram watermark default: @aj__editz_2.0.
