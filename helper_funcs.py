"""
    Набор функций для работы с изображениями - определения прозрачности и конвертации.
"""
# pylint: disable=line-too-long
import os
import logging
import errno

from i18n import t
import PIL.Image
import PIL.ImageOps

TARGET_OPAQUE_EXTENSION = ".png"  # Расширение, в котором будут сохраняться изображения без прозрачности.
TARGET_TRANSPARENT_EXTENSION = ".tga"  # Расширение, в котором будут сохраняться изображения с прозрачностью.


def has_transparency(img_object: PIL.Image.Image) -> bool:
    """
    Проверка изображения на наличие частичной или полной прозрачности пикселей.
    :param img_object: Изображение.
    :return: Является ли изображение частично или полностью прозрачным.
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
    :param img_object: Изображение.
    :param fpe: Путь к файлу без расширения.
    :param ext: Расширение файла с точкой.
    :return: Путь к сохранённому файлу.
    """
    if img_object is None:
        return ""
    fp = fpe + ext
    try:
        if ext.lower() == ".tga":  # Файлы TGA можно сжать, используя RLE сжатие.
            img_object.save(fp, optimize=True, quality=100, compression="tga_rle")
        else:
            img_object.save(fp, optimize=True, quality=100)
    except OSError as e:
        logging.info(t("helper_funcs.exception_save"), fp)
        logging.info(e)
        return ""
    return fp


def resave_img(img_object: PIL.Image.Image) -> str:
    """
    Сохранение изображения в другом формате в зависимости от наличия в нём прозрачности и RLE-сжатия
    для случая TGA.
    :param img_object: Изображение.
    :return: Путь к сохранённому файлу или пустая строка, если файл уже в нужном формате.
    """
    fp = getattr(img_object, "filename", "")
    if fp == "":
        raise FileNotFoundError
    fpe, ext = os.path.splitext(fp)
    ext = ext.lower()
    if not has_transparency(img_object):  # Изображение непрозрачное.
        if ext != TARGET_OPAQUE_EXTENSION.lower() and os.path.exists(
                fpe + TARGET_OPAQUE_EXTENSION):  # Существует другой файл с новым путём.
            raise FileExistsError(errno.EEXIST, t("main.file_already_exists") %
                                  (fpe + TARGET_OPAQUE_EXTENSION))
        if ext == TARGET_OPAQUE_EXTENSION.lower() and img_object.mode == "RGB":  # Изображение уже
            # в нужном формате.
            return ""
        if img_object.mode != "RGB":
            img_object = img_object.convert("RGB")
        return save_image(img_object, fpe, TARGET_OPAQUE_EXTENSION)
    if ext != TARGET_TRANSPARENT_EXTENSION.lower() and os.path.exists(
            fpe + TARGET_TRANSPARENT_EXTENSION):  # Существует другой файл с новым путём.
        raise FileExistsError(errno.EEXIST, t("main.file_already_exists") %
                              (fpe + TARGET_TRANSPARENT_EXTENSION))
    if ext == TARGET_TRANSPARENT_EXTENSION.lower() and img_object.mode == "RGBA" and (
            TARGET_TRANSPARENT_EXTENSION.lower() != ".tga" or (
            "compression" in img_object.info and img_object.info["compression"]
            == "tga_rle")):  # Изображение уже
        # в нужном формате.
        return ""
    if img_object.mode != "RGBA":
        img_object = img_object.convert("RGBA")
    return save_image(img_object, fpe, TARGET_TRANSPARENT_EXTENSION)


def mirror_concat_img(img_object: PIL.Image.Image) -> str:
    """
    Добавление справа от изображения его отзеркаленной версии и сохранение вместо начального.
    :param img_object: Изображение.
    :return: Путь к сохранённому файлу (совпадает с начальным).
    """
    fp = getattr(img_object, "filename", "")
    if fp == "":
        raise FileNotFoundError
    fpe, ext = os.path.splitext(fp)
    img_concat = PIL.Image.new(img_object.mode, (img_object.size[0] * 2, img_object.size[1]))
    img_concat.paste(img_object, (0, 0))
    img_concat.paste(PIL.ImageOps.mirror(img_object), (img_object.size[0], 0))
    return save_image(img_concat, fpe, ext)


def split_eyes_img(img_object: PIL.Image.Image) -> list[str]:
    """
    Разделение текстуры глаз/рта на 8 изображений и их сохранение.
    :param img_object: Изображение.
    :return: Путь к сохранённым файлам.
    """
    fp = getattr(img_object, "filename", "")
    if fp == "":
        raise FileNotFoundError
    if img_object.size[0] % 2 != 0 or img_object.size[1] % 4 != 0:
        raise IOError(errno.EIO, t("main.img_split_eyes_wrong_resolution") % (
        fp, img_object.size[0], img_object.size[1]))
    fpe, ext = os.path.splitext(fp)
    result_paths = []
    for i in range(4):
        y0 = i * img_object.size[1] // 4
        y1 = (i + 1) * img_object.size[1] // 4
        x0 = 0
        x1 = img_object.size[0] // 2
        img_cropped_right = img_object.crop((x0, y0, x1, y1))
        img_cropped_left = PIL.ImageOps.mirror(img_cropped_right)
        img_concat = PIL.Image.new(img_object.mode,
                                   (img_object.size[0], img_object.size[1] // 4))
        img_concat.paste(img_cropped_left, (0, 0))
        img_concat.paste(img_cropped_right, (img_object.size[0] // 2, 0))
        result_paths.append(save_image(img_concat, fpe + "_" + str(i + 1), ext))
        x0 = img_object.size[0] // 2
        x1 = img_object.size[0]
        img_cropped_left = img_object.crop((x0, y0, x1, y1))
        img_cropped_right = PIL.ImageOps.mirror(img_cropped_left)
        img_concat = PIL.Image.new(img_object.mode,
                                   (img_object.size[0], img_object.size[1] // 4))
        img_concat.paste(img_cropped_left, (0, 0))
        img_concat.paste(img_cropped_right, (img_object.size[0] // 2, 0))
        result_paths.append(save_image(img_concat, fpe + "_" + str(i + 5), ext))
    return result_paths
