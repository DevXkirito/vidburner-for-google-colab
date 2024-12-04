import os
import subprocess
from PIL import ImageFont
import matplotlib.font_manager as fm
import ffmpeg as ffmpeg_lib

def is_font_installed(font_name):
    for font in fm.findSystemFonts(fontpaths=None, fontext='ttf'):
        if font_name in font:
            return True
    return False

def install_font(font_path):
    font_name = os.path.splitext(os.path.basename(font_path))[0]
    if not is_font_installed(font_name):
        subprocess.run(['fc-cache', '-f', '-v'], check=True)
        print(f"Installed font: {font_name}")
    else:
        print(f"Font {font_name} is already installed.")
    return font_name

def find_font_name(font_path):
    font = ImageFont.truetype(font_path, size=12)
    return font.getname()[0]

def burn_subtitles_with_font_and_size(input_video, subtitle_file, output_video, font_path, font_size, alignment, margin_vertical):
    font_name = find_font_name(font_path)
    (
        ffmpeg_lib
        .input(input_video)
        .output(
            output_video, 
            vf=f"subtitles={subtitle_file}:force_style='FontName={font_name},FontSize={font_size},Alignment={alignment},MarginV={margin_vertical}'"
        )
        .run(overwrite_output=True)
    )
