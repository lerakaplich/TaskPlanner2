# convert_png_to_ico.py
import sys
import os
from PIL import Image


def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def convert_png_to_ico(png_path, ico_path=None, sizes=None):
    """Конвертация PNG в ICO с поддержкой 256x256"""
    if ico_path is None:
        ico_path = os.path.splitext(png_path)[0] + '.ico'

    # Стандартные размеры для Windows иконок (включая 256x256)
    if sizes is None:
        sizes = [
            (16, 16),  # Маленькие значки
            (24, 24),  # Средние значки
            (32, 32),  # Стандартные значки
            (48, 48),  # Крупные значки
            (64, 64),  # Очень крупные
            (128, 128),  # Экстра крупные
            (256, 256)  # Максимальный размер для Windows
        ]

    print(f"📷 Исходное изображение: {png_path}")
    img = Image.open(png_path)
    print(f"   Размер: {img.size[0]}x{img.size[1]}, режим: {img.mode}")

    # Конвертируем в RGBA если нужно
    if img.mode != 'RGBA':
        print(f"   🔄 Конвертируем из {img.mode} в RGBA")
        img = img.convert('RGBA')

    # Создаём и сохраняем иконку с несколькими размерами
    # Важно: используем правильный метод сохранения ICO
    img.save(
        ico_path,
        format='ICO',
        sizes=sizes,
        quality=100
    )

    print(f"✅ Конвертировано: {png_path} → {ico_path}")
    print(f"📦 Размер файла: {os.path.getsize(ico_path)} байт")

    # Проверяем созданную иконку
    try:
        with Image.open(ico_path) as verify_img:
            # Получаем все размеры из иконки
            icon_sizes = []
            try:
                # Для PIL/Pillow > 8.0
                icon_sizes = verify_img.info.get('sizes', [])
                if not icon_sizes:
                    # Альтернативный способ получить размеры
                    verify_img.seek(0)
                    icon_sizes.append(verify_img.size)
                    frame = 1
                    while True:
                        try:
                            verify_img.seek(frame)
                            icon_sizes.append(verify_img.size)
                            frame += 1
                        except EOFError:
                            break
            except:
                icon_sizes = [verify_img.size]

            print(f"🔍 Иконка содержит размеры: {icon_sizes}")

            # Проверяем наличие 256x256
            if (256, 256) in icon_sizes:
                print(f"🎉 Успех! Размер 256x256 присутствует в иконке!")
            else:
                print(f"⚠️ Внимание! Размер 256x256 отсутствует. Доступны: {icon_sizes}")
    except Exception as e:
        print(f"⚠️ Не удалось проверить иконку: {e}")

    return ico_path


def create_multi_resolution_icon(source_png, output_dir=None):
    """Создаёт иконку из PNG с разными разрешениями"""
    if output_dir is None:
        output_dir = os.path.dirname(source_png)

    if not output_dir:
        output_dir = "."

    # Путь для сохранения
    ico_path = os.path.join(output_dir, 'taskplanner.ico')

    # Все необходимые размеры (обязательно включая 256x256)
    sizes = [
        (16, 16),  # Для системного трея
        (24, 24),  # Для меню Пуск
        (32, 32),  # Для стандартных значков
        (48, 48),  # Для папок и файлов
        (64, 64),  # Для крупных значков
        (128, 128),  # Для очень крупных
        (256, 256)  # Для рабочего стола и предпросмотра
    ]

    return convert_png_to_ico(source_png, ico_path, sizes)


if __name__ == "__main__":
    # Путь к исходному PNG
    source_images = [
        "images/taskplanner_icon.png"
    ]

    # Ищем существующий файл
    source_png = None
    for img_path in source_images:
        full_path = os.path.join(os.getcwd(), img_path)
        if os.path.exists(full_path):
            source_png = full_path
            break
        elif os.path.exists(img_path):
            source_png = img_path
            break

    if source_png and os.path.exists(source_png):
        print(f"🎨 Найден исходный файл: {source_png}")

        # Создаём папку images если её нет
        os.makedirs("images", exist_ok=True)

        # Создаём иконку
        ico_path = create_multi_resolution_icon(source_png, "images")

        print(f"\n✨ Иконка готова: {ico_path}")
        print(f"\n📌 Для использования в PyInstaller:")
        print(f'   pyinstaller --icon "{ico_path}" ...')
        print(f"\n📌 Для Inno Setup:")
        print(f'   SetupIconFile={ico_path}')

        # Дополнительная проверка с помощью системного просмотрщика
        print(
            f"\n💡 Совет: Откройте {ico_path} в проводнике Windows, чтобы убедиться, что иконка отображается правильно.")

    else:
        print("❌ Не найден исходный PNG файл!")
        print("Пожалуйста, убедитесь, что у вас есть файл:")
        for img_path in source_images:
            print(f"   - {img_path}")
        print("\nИли укажите правильный путь в переменной source_images")