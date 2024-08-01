import os
import logging
import PIL.Image

target_opaque_extension = ".png"  # Расширение, в котором будут сохраняться изображения без прозрачности.
target_transparent_extension = ".tga"  # Расширение, в котором будут сохраняться изображения с прозрачностью.


def has_transparency(img_object: PIL.Image.Image) -> bool:
    """
    Проверка изображения на наличие частичной или полной прозрачности пикселей.
    :param img_object: Изображение
    :return: Является ли изображение частично или полностью прозрачным
    """
    if img_object.mode == "P":
        transparent = img_object.info.get("transparency", -1)
        for _, index in img_object.getcolors():
            if index == transparent:
                return True
    elif img_object.mode == "RGBA":
        extrema = img_object.getextrema()
        if extrema[3][0] < 255:
            return True
    return False


def save_image(img_object: PIL.Image.Image, fpe: str, ext: str) -> str:
    """
    Сохранение изображения с заданным именем и расширением.
    :param img_object: Изображение
    :param fpe: Путь к файлу без расширения
    :param ext: Расширение файла с точкой
    :return: Путь к сохранённому файлу
    """
    if img_object is None:
        return ""
    fp = fpe + ext
    try:
        if ext.lower() == ".tga":  # Файлы TGA можно сжать, используя RLE сжатие.
            img_object.save(fp, optimize=True, quality=100, compression="tga_rle")
        else:
            img_object.save(fp, optimize=True, quality=100)
    except Exception as exc:
        logging.info("Исключение при попытке сохранения " + fp + ":")
        logging.info(exc)
        return ""
    return fp


def resave_img(img_object: PIL.Image.Image) -> str:
    """
    Сохранение изображения в другом формате в зависимости от наличия в нём прозрачности и RLE-сжатия для случая TGA.
    :param img_object: Изображение
    :return: Путь к сохранённому файлу или пустая строка, если файл уже в нужном формате.
    """
    fp = getattr(img_object, "filename", "")
    if fp == "":
        raise FileNotFoundError
    fpe, ext = os.path.splitext(fp)
    ext = ext.lower()
    if not has_transparency(img_object):  # Изображение непрозрачное.
        if ext != target_opaque_extension.lower() and os.path.exists(
                fpe + target_opaque_extension):  # Существует другой файл с новым путём.
            raise FileExistsError
        if ext == target_opaque_extension.lower() and img_object.mode == "RGB":  # Изображение уже в нужном формате.
            return ""
        if img_object.mode != "RGB":
            img_object = img_object.convert("RGB")
        return save_image(img_object, fpe, target_opaque_extension)
    if ext != target_transparent_extension.lower() and os.path.exists(
            fpe + target_transparent_extension):  # Существует другой файл с новым путём.
        raise FileExistsError
    if ext == target_transparent_extension.lower() and img_object.mode == "RGBA" and (
            ext != ".tga" or getattr(img_object.info, "compression") == "tga_rle"):  # Изображение уже в нужном формате.
        return ""
    if img_object.mode != "RGBA":
        img_object = img_object.convert("RGBA")
    return save_image(img_object, fpe, target_transparent_extension)
