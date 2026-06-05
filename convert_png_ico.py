# convert_png_to_ico.py
import sys

from PIL import Image
import os

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def convert_png_to_ico(png_path, ico_path=None, sizes=None):
    """Конвертация PNG в ICO"""
    if ico_path is None:
        ico_path = os.path.splitext(png_path)[0] + '.ico'

    if sizes is None:
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    # Загружаем PNG
    img = Image.open(png_path)

    # Конвертируем в RGBA если нужно
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Создаем иконку с разными размерами
    icon_sizes = []
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icon_sizes.append(resized)

    # Сохраняем как ICO
    icon_sizes[0].save(
        ico_path,
        format='ICO',
        sizes=[(s.width, s.height) for s in icon_sizes],
        append_images=icon_sizes[1:] if len(icon_sizes) > 1 else None
    )

    print(f"✅ Конвертировано: {png_path} → {ico_path}")
    return ico_path


if __name__ == "__main__":
    # Конвертируем logo.png в logo.ico
    convert_png_to_ico(resource_path("taskplanner.png"))