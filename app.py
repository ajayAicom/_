from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from engine import (
    ASPECT_SIZES,
    PHOTO_PRESETS,
    STYLE_CONFIG,
    create_story_assets,
    generate_photo_canvas,
    generate_video,
    get_photo_size,
    process_uploaded_photo,
)

st.set_page_config(
    page_title="MotionAI 30s - Video + Photo Generator",
    page_icon="🎬",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main {background: #0f1117; color: white;}
        .stButton button {width: 100%; border-radius: 12px; font-weight: 700;}
        .block-container {padding-top: 2rem;}
        div[data-testid="stMetricValue"] {font-size: 1.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎬 MotionAI 30s")
st.caption("Video maker + photo generator/resizer. Photo reference ho ya na ho, dono flow supported. Free local render.")

video_tab, photo_tab = st.tabs(["🎥 Video Maker", "🖼️ Photo Generator / Resizer"])

with video_tab:
    with st.sidebar:
        st.header("Video Settings")
        mode = st.radio(
            "Creation Mode",
            ["Photo Reference Mode", "No Photo Story Mode"],
            index=0,
            help="Photo mode me uploaded images use hongi. Story mode me app topic se scenes generate karega.",
        )
        language = st.selectbox("Video Language", ["Hinglish", "Hindi", "English"], index=0, key="video_language")
        tone = st.selectbox("Story Tone", ["Promotional", "Cinematic", "Emotional", "Informative"], index=0)
        duration = st.slider("Duration", min_value=5, max_value=30, value=30, step=1)
        aspect = st.selectbox("Aspect Ratio", list(ASPECT_SIZES.keys()), index=1)
        resolution = st.selectbox("Resolution", ["720p", "1080p"], index=0)
        style = st.selectbox("Motion Style", list(STYLE_CONFIG.keys()), index=0)
        fps = st.selectbox("FPS", [24, 30, 60], index=0)
        transition = st.slider("Transition Smoothness", min_value=0.0, max_value=1.2, value=0.65, step=0.05)
        scene_count = st.slider("Story/Scene Count", min_value=3, max_value=8, value=6, step=1)

        st.divider()
        watermark_mode = st.selectbox("Watermark", ["No Watermark", "Instagram ID"], index=0)
        instagram_handle = ""
        watermark_position = "Bottom Right"
        if watermark_mode == "Instagram ID":
            instagram_handle = st.text_input("Instagram ID", value="@aj__editz_2.0")
            watermark_position = st.selectbox("Watermark Position", ["Bottom Right", "Bottom Left", "Top Right", "Top Left"], index=0)
            st.caption("Transparent Instagram-style icon + ID video ke upar add hoga.")

        st.divider()
        output_name = st.text_input("Video file name", value="my_motion_video")
        st.caption("Example: cake_promo_30sec, product_ad, travel_reel")

    left, right = st.columns([1, 1])

    with left:
        st.subheader("1. Input")
        story_prompt = st.text_area(
            "Story / Topic Prompt",
            value="Premium bakery product promo with smooth motion graphics",
            height=95,
            help="Photo na ho to isi prompt/topic se scenes banenge. Photo mode me bhi captions improve karne ke kaam aayega.",
        )

        photos = []
        if mode == "Photo Reference Mode":
            photos = st.file_uploader(
                "Reference photos upload karo",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
            )
        else:
            st.info("No Photo Story Mode: koi photo upload zaroori nahi. App prompt/topic se scenes generate karega.")

        logo = st.file_uploader("Optional custom logo upload", type=["jpg", "jpeg", "png", "webp"])
        music = st.file_uploader("Optional background music", type=["mp3", "wav", "m4a", "aac"])

        st.subheader("2. Captions / Text")
        caption_text = st.text_area(
            "Optional manual captions. Har line ek scene/caption banegi. Title | subtitle format use kar sakte ho.",
            value="",
            height=120,
            placeholder="Premium Product | Fresh, clean and professional\nOrder Now | Fast service and trusted quality",
        )

    with right:
        st.subheader("3. Generate")
        c1, c2, c3 = st.columns(3)
        c1.metric("Max", "30 sec")
        c2.metric("Modes", "2")
        c3.metric("Cost", "Local/free")

        st.write("Photo mode me uploaded images animate hongi. Story mode me app topic se scenes banakar motion graphics video export karega.")
        st.info("Firebase Hosting ke liye static browser version bhi ZIP me `firebase-web/` folder ke andar diya gaya hai.")

        generate = st.button("Generate Video", type="primary")

        if generate:
            workdir = Path(tempfile.mkdtemp(prefix="motionai_"))
            image_paths = []
            temp_story_paths = []

            try:
                manual_captions = [line.strip() for line in caption_text.splitlines() if line.strip()]

                if mode == "Photo Reference Mode":
                    if not photos:
                        st.error("Photo Reference Mode me kam se kam 1 photo upload karo. Ya No Photo Story Mode select karo.")
                        st.stop()
                    for i, file in enumerate(photos):
                        suffix = Path(file.name).suffix or ".png"
                        out = workdir / f"photo_{i}{suffix}"
                        out.write_bytes(file.read())
                        image_paths.append(str(out))
                    captions = manual_captions or None
                else:
                    image_paths, story_captions = create_story_assets(
                        topic=story_prompt,
                        language=language,
                        tone=tone,
                        aspect=aspect,
                        resolution=resolution,
                        style=style,
                        scene_count=scene_count,
                    )
                    temp_story_paths = image_paths
                    captions = manual_captions or story_captions

                logo_path = None
                if logo:
                    logo_path = workdir / f"logo{Path(logo.name).suffix or '.png'}"
                    logo_path.write_bytes(logo.read())

                music_path = None
                if music:
                    music_path = workdir / f"music{Path(music.name).suffix or '.mp3'}"
                    music_path.write_bytes(music.read())

                progress = st.progress(0, text="Video render start ho raha hai...")
                progress.progress(15, text="Scenes prepare ho rahe hain...")
                output_path = generate_video(
                    image_paths=image_paths,
                    output_name=output_name,
                    output_dir="outputs",
                    duration=duration,
                    aspect=aspect,
                    resolution=resolution,
                    style=style,
                    captions=captions,
                    fps=fps,
                    transition=transition,
                    music_path=str(music_path) if music_path else None,
                    logo_path=str(logo_path) if logo_path else None,
                    watermark_handle=instagram_handle if watermark_mode == "Instagram ID" else None,
                    watermark_position=watermark_position,
                )
                progress.progress(100, text="Done")
                st.success("Video ready!")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button(
                        "Download MP4",
                        data=f,
                        file_name=os.path.basename(output_path),
                        mime="video/mp4",
                    )
            except Exception as exc:
                st.error(f"Render failed: {exc}")
                st.write("Tip: 1080p heavy ho sakta hai. Pehle 720p + 24 FPS try karo.")
            finally:
                for path in temp_story_paths:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

with photo_tab:
    st.subheader("Photo Generator + Resize/Compress")
    st.write("Yahan se 1:1, 9:16, 16:9, 400×400, A4, custom size aur KB/MB target ke saath image export kar sakte ho.")

    p_left, p_right = st.columns([1, 1])

    with p_left:
        photo_mode = st.radio(
            "Photo Mode",
            ["Generate from prompt", "Edit / Resize uploaded photo"],
            index=0,
            horizontal=True,
        )
        photo_language = st.selectbox("Photo Language", ["Hinglish", "Hindi", "English"], index=0, key="photo_language")
        photo_style = st.selectbox("Photo Style", list(STYLE_CONFIG.keys()), index=1, key="photo_style")
        photo_preset = st.selectbox("Output Size / Ratio", list(PHOTO_PRESETS.keys()), index=1)

        custom_w, custom_h = 1080, 1080
        if photo_preset == "Custom Size":
            c_w, c_h = st.columns(2)
            custom_w = c_w.number_input("Width px", min_value=64, max_value=4096, value=1080, step=10)
            custom_h = c_h.number_input("Height px", min_value=64, max_value=4096, value=1080, step=10)

        final_w, final_h = get_photo_size(photo_preset, int(custom_w), int(custom_h))
        st.caption(f"Final size: {final_w} × {final_h} px")

        photo_file_name = st.text_input("Photo file name", value="motionai_photo")
        output_format = st.selectbox("Export Format", ["JPG", "PNG", "WEBP"], index=0)

        photo_watermark_mode = st.selectbox("Photo Watermark", ["No Watermark", "Instagram ID"], index=0)
        photo_instagram_handle = ""
        photo_watermark_position = "Bottom Right"
        if photo_watermark_mode == "Instagram ID":
            photo_instagram_handle = st.text_input("Photo Instagram ID", value="@aj__editz_2.0")
            photo_watermark_position = st.selectbox("Photo Watermark Position", ["Bottom Right", "Bottom Left", "Top Right", "Top Left"], index=0)
            st.caption("Transparent Instagram-style icon + ID photo export me add hoga.")

        use_target_size = st.checkbox("Target file size set karo (KB/MB)", value=True)
        target_size_value = None
        target_size_unit = "KB"
        if use_target_size:
            s1, s2 = st.columns([2, 1])
            target_size_value = s1.number_input("Target size", min_value=10.0, max_value=50_000.0, value=200.0, step=10.0)
            target_size_unit = s2.selectbox("Unit", ["KB", "MB"], index=0)
            st.caption("JPG/WEBP me target size close milega. PNG exact compress nahi hota.")

        if photo_mode == "Generate from prompt":
            photo_prompt = st.text_area(
                "Photo prompt / topic",
                value="Premium bakery product poster, clean professional design",
                height=110,
                placeholder="Example: Cake shop Diwali offer poster, red white premium background",
            )
            uploaded_photo = None
            fit_mode = "Smart Crop"
            bg_color = "#FFFFFF"
        else:
            uploaded_photo = st.file_uploader("Photo upload karo", type=["jpg", "jpeg", "png", "webp"], key="photo_upload")
            fit_mode = st.selectbox("Fit Mode", ["Smart Crop", "Fit / No Crop", "Stretch"], index=0)
            bg_color = st.color_picker("Background color for Fit / No Crop", value="#FFFFFF")
            photo_prompt = ""

        make_photo = st.button("Generate / Export Photo", type="primary")

    with p_right:
        st.subheader("Preview / Download")
        if make_photo:
            workdir = Path(tempfile.mkdtemp(prefix="motionai_photo_"))
            try:
                if photo_mode == "Generate from prompt":
                    output_path = generate_photo_canvas(
                        prompt=photo_prompt,
                        language=photo_language,
                        style=photo_style,
                        output_name=photo_file_name,
                        output_dir="outputs",
                        preset=photo_preset,
                        custom_width=int(custom_w),
                        custom_height=int(custom_h),
                        output_format=output_format,
                        target_size_value=target_size_value,
                        target_size_unit=target_size_unit,
                        watermark_handle=photo_instagram_handle if photo_watermark_mode == "Instagram ID" else None,
                        watermark_position=photo_watermark_position,
                    )
                else:
                    if not uploaded_photo:
                        st.error("Edit/Resize mode me photo upload karo.")
                        st.stop()
                    src = workdir / f"uploaded{Path(uploaded_photo.name).suffix or '.png'}"
                    src.write_bytes(uploaded_photo.read())
                    output_path = process_uploaded_photo(
                        image_path=src,
                        output_name=photo_file_name,
                        output_dir="outputs",
                        preset=photo_preset,
                        custom_width=int(custom_w),
                        custom_height=int(custom_h),
                        fit_mode=fit_mode,
                        background_color=bg_color,
                        output_format=output_format,
                        target_size_value=target_size_value,
                        target_size_unit=target_size_unit,
                        watermark_handle=photo_instagram_handle if photo_watermark_mode == "Instagram ID" else None,
                        watermark_position=photo_watermark_position,
                    )

                size_bytes = os.path.getsize(output_path)
                st.success("Photo ready!")
                st.image(output_path, use_container_width=True)
                st.metric("Output size", f"{size_bytes / 1024:.1f} KB")
                mime = {"JPG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(output_format, "image/jpeg")
                with open(output_path, "rb") as f:
                    st.download_button(
                        "Download Photo",
                        data=f,
                        file_name=os.path.basename(output_path),
                        mime=mime,
                    )
            except Exception as exc:
                st.error(f"Photo export failed: {exc}")

st.divider()
st.markdown(
    """
    ### Included tools
    - **Video Maker:** photo reference video + no-photo story video, 30 sec max.
    - **Photo Generator:** prompt se AI-style poster/photo graphic.
    - **Photo Resizer:** uploaded photo ko 1:1, 400×400, 9:16, 16:9, A4, custom size me export.
    - **Compression:** JPG/WEBP me KB/MB target ke aas-paas output.
    - **Watermark:** No watermark ya transparent Instagram-style logo + your Insta ID.
    - **Firebase:** `firebase-web/` folder me browser-based Hosting version included hai.
    """
)
