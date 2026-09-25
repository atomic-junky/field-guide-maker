import importlib
import io
import json
import math
from pathlib import Path

from PIL import Image
import streamlit as st
from streamlit.proto.FileUploader_pb2 import FileUploader

from .factory import FieldGuideFactory
from .models import Settings


def generate_html_preview(
    settings: Settings
):
    inset_x_pct = (settings.outer_margin[0] / settings.canvas_size[0]) * 50
    inset_y_pct = (settings.outer_margin[1] / settings.canvas_size[1]) * 50
    
    action_margin: int = (1 - settings.action_safe_scale) * 50
    title_margin: int = (1 - settings.title_safe_scale) * 50

    outer_aspect_ratio = f"{settings.canvas_size[0]} / {settings.canvas_size[1]}"

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
        {f'''<div style="position: absolute; top: 0; bottom: 0; left: 0; right: 0; border: 1px solid #ff00ff; pointer-events: none;"></div>''' if settings.display_overscan else ""}

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
            </div>''' if settings.display_cross else ""}

            {f'''<div style="position: absolute; top: {title_margin}%; bottom: {title_margin}%; left: {title_margin}%; right: {title_margin}%; border: 2px solid {settings.title_border_color}; pointer-events: none;"></div>''' if settings.display_title_safe else ""}

            {f'''<div style="position: absolute; top: {action_margin}%; bottom: {action_margin}%; left: {action_margin}%; right: {action_margin}%; border: 2px solid {settings.action_border_color}; pointer-events: none;"></div>''' if settings.display_action_safe else ""}
        </div>
    </div>
    """
    return st.html(html_code)


def init_gui() -> None:
    s = Settings()
    
    im = Image.open(Path(__file__).parent / "assets" / "fgm_logo.png")
    st.set_page_config(page_title="Field Guide Maker", page_icon=im, layout="centered")

    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.title("Field Guide Maker")
        st.space("stretch")
        
        version = importlib.metadata.version('field_guide_maker')
        st.caption("v" + version, text_alignment="right")
    st.logo("./src/fgm/assets/fgm_logo.svg")
    st.caption("Generate your base PSD for animation background layouts.")
    st.divider()

    with st.container(horizontal=True):
        st.subheader("Configuration")
        st.space("stretch")

    colc, colp = st.columns(2)
    with colc:
        colw, colh = st.columns(2)
        with colw:
            s.width = st.number_input("Width", min_value=1, value=s.width)
        with colh:
            s.height = st.number_input("Height", min_value=1, value=s.height)

        st.text(
            f"Aspect Ratio: {int(s.width/s.ratio)}:{int(s.height/s.ratio)} ({(s.width/s.height):.2f})"
        )

        s._safe_margin_input = st.number_input(
            "Safe Margin (in %)", min_value=0, value=s._safe_margin_input
        )
        s.absolute_margin = st.checkbox("Absolute Margin", value=False)

    st.space("small")

    s.display_cross = st.checkbox("Cross", value=s.display_cross)
    s.display_title_safe = st.checkbox("Title Safe Border", value=s.display_title_safe)
    s.display_action_safe = st.checkbox("Action Safe Border", value=s.display_action_safe)
    s.display_overscan = st.checkbox("Overscan Border", value=s.display_overscan)

    with st.expander("Advanced Settings"):
        with st.container(horizontal=True):
            s._action_safe_scale_input = st.number_input(
                "Action Safe Margins (in %)", min_value=0, value=s._action_safe_scale_input
            )
            
            s._title_safe_scale_input = st.number_input(
                "Title Safe Margins (in %)", min_value=0, value=s._title_safe_scale_input
            )
        
        st.write("Border Colors")
        with st.container(horizontal=True):
            s.border_color = st.color_picker("Border", width="stretch", value=s.border_color)
            s.overscan_border_color = st.color_picker("Overscan", width="stretch", value=s.overscan_border_color)
            s.action_border_color = st.color_picker("Action", width="stretch", value=s.action_border_color)
            s.title_border_color = st.color_picker("Title", width="stretch", value=s.title_border_color)
            s.cross_color = st.color_picker("Cross", width="stretch", value=s.cross_color)
        
        # st.write("Import/Export config")
        # with st.container(horizontal=True, vertical_alignment="center"):
        #     st.download_button(
        #         label="Export",
        #         data=s.to_json(),
        #         file_name="fgm_config.json",
        #         mime="json",
        #         icon=":material/download:",
        #     )
            
        #     config_file = st.file_uploader(
        #         "Import",
        #         type=".json",
        #         label_visibility="collapsed"
        #     )
            
        #     if config_file is not None:
        #         try:
        #             stringio = io.StringIO(config_file.getvalue().decode("utf-8"))
        #             st.write(stringio)
        #             raw_data = stringio.read()
        #             data = json.loads(raw_data)
        #             s = s.from_json(data)
        #         except:
        #             print("Failed to load config file.")

    with colp:
        colp.border = True
        generate_html_preview(s)

    def _export_callback() -> io.BytesIO:
        factory = FieldGuideFactory(s)

        data = io.BytesIO()
        factory.save(data)
        data.seek(0)
        return data

    st.space("small")

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