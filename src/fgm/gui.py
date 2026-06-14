import io
import math
from pathlib import Path

from PIL import Image
import streamlit as st
from fgm.factory import FGMFactory, FGMConfig


def generate_html_preview(
    width: int,
    height: int,
    safe_margin: float,
    absolute_margin: bool,
    display_cross: bool,
    display_action_safe: bool,
    display_title_safe: bool,
    display_overscan: bool,
):
    if absolute_margin:
        margin_px = (max(width, height) * safe_margin) / 2

        outer_width = width + (2 * margin_px)
        outer_height = height + (2 * margin_px)

        outer_aspect_ratio = f"{outer_width} / {outer_height}"

        inset_x_pct = (margin_px / outer_width) * 100
        inset_y_pct = (margin_px / outer_height) * 100
    else:
        total_scale = 1 + safe_margin
        inset_pct = (safe_margin / (2 * total_scale)) * 100

        outer_aspect_ratio = f"{width} / {height}"
        inset_x_pct = inset_pct
        inset_y_pct = inset_pct

    html_code: str = f"""
    <div style="
        width: 100%; 
        aspect-ratio: {outer_aspect_ratio}; 
        background-color: #404040; 
        position: relative; 
        overflow: hidden;
        border-radius: 4px;
        box-shadow: inset 0 0 0 1px rgba(250, 250, 250, 0.2);
    ">
        {f'''<div style="position: absolute; top: 0; bottom: 0; left: 0; right: 0; border: 1px solid #ff00ff; pointer-events: none;"></div>''' if display_overscan else ""}

        <div style="
            position: absolute; 
            top: {inset_y_pct}%; 
            bottom: {inset_y_pct}%; 
            left: {inset_x_pct}%; 
            right: {inset_x_pct}%; 
            background-color: #fff; 
            border: 2px solid #0000ff;
        ">
            {f'''<div style="position: absolute; top: 0; bottom: 0; left: 0; right: 0; pointer-events: none; background-image: 
                linear-gradient(to bottom right, transparent calc(50% - 1px), rgba(0, 255, 0, 255) 50%, transparent calc(50% + 1px)),
                linear-gradient(to top right, transparent calc(50% - 1px), rgba(0, 255, 0, 255) 50%, transparent calc(50% + 1px));">
            </div>''' if display_cross else ""}

            {f'''<div style="position: absolute; top: 10%; bottom: 10%; left: 10%; right: 10%; border: 2px solid #00ffff; pointer-events: none;"></div>''' if display_title_safe else ""}

            {f'''<div style="position: absolute; top: 15%; bottom: 15%; left: 15%; right: 15%; border: 2px solid #00ffff; pointer-events: none;"></div>''' if display_action_safe else ""}
        </div>
    </div>
    """
    return st.html(html_code)


def init_gui() -> None:
    im = Image.open(Path(__file__).parent / "assets" / "fgm_logo.png")
    st.set_page_config(page_title="Field Guide Maker", page_icon=im, layout="centered")

    st.title("Field Guide Maker")
    st.caption("Create your base PSD file for your animation background layout.")
    st.divider()

    st.subheader("Configuration")

    colc, colp = st.columns(2)
    with colc:
        colw, colh = st.columns(2)
        with colw:
            width_input = st.number_input("Width", min_value=1, value=1920)
        with colh:
            height_input = st.number_input("Height", min_value=1, value=1080)

        ratio = math.gcd(width_input, height_input)
        st.text(
            f"Aspect Ratio: {int(width_input/ratio)}:{int(height_input/ratio)} ({width_input/height_input:.2f})"
        )

        safe_margin_input: int = st.number_input(
            "Safe Margin (in %)", min_value=0, value=15
        )
        safe_margin_value = safe_margin_input / 100.0
        absolute_margin = st.checkbox("Absolute Margin", value=False)

        st.write("")

        display_cross = st.checkbox("Cross", value=True)
        display_action_safe = st.checkbox("Action Safe Border", value=True)
        display_title_safe = st.checkbox("Title Safe Border", value=True)
        display_overscan = st.checkbox("Overscan Border", value=True)

    with colp:
        colp.border = True
        generate_html_preview(
            width_input,
            height_input,
            safe_margin_value,
            absolute_margin,
            display_cross,
            display_action_safe,
            display_title_safe,
            display_overscan,
        )

    def _export_callback() -> io.BytesIO:
        config = FGMConfig(
            width=width_input,
            height=height_input,
            safe_margin=safe_margin_value,
            absolute_margin=absolute_margin,
            draw_cross=display_cross,
            action_border=display_action_safe,
            title_border=display_title_safe,
            overscan_border=display_overscan,
        )
        factory = FGMFactory(config)

        data = io.BytesIO()
        factory.save(data)
        data.seek(0)
        return data

    st.write("")

    with st.container(horizontal=True, vertical_alignment="bottom"):
        file_name: str = st.text_input(
            label="File Name",
            value="field_guide.psd",
            key="file_name_input",
        )

        st.download_button(
            label="Export",
            data=_export_callback,
            file_name=file_name,
            mime="image/vnd.adobe.photoshop",
        )


if __name__ == "__main__":
    init_gui()
