"""
    Скрипт, добавляющий справа от изображений их зеркальную копию.
"""
# pylint: disable=import-error, duplicate-code
import os
import sys
import argparse
import logging
from tkinter.filedialog import askopenfilenames
from concurrent.futures import ThreadPoolExecutor, as_completed
from i18n import t
import PIL.Image
import PIL.ImageTk
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from main import prepare_app, SUPPORTED_EXTENSIONS
from helper_funcs import mirror_concat_img


def execute_mirror_concat(img_paths: list[str]) -> str | int:
    """
    Добавление справа от изображений их отзеркаленных версий и сохранение вместо начальных.
    :param img_paths: Пути к изображениям.
    :return: Код ошибки или строка с ошибкой.
    """
    if len(img_paths) < 1:
        return os.EX_OK
    with logging_redirect_tqdm():
        pbar = tqdm(total=len(img_paths), desc=t("main.files"))
        with ThreadPoolExecutor() as executor:
            future_images = {executor.submit(mirror_concat_file, img_path): img_path for img_path in
                             img_paths}
            for future in as_completed(future_images):
                img_path = future_images[future]
                pbar.set_postfix_str(img_path)
                try:
                    future.result()
                except PIL.UnidentifiedImageError:
                    logging.info(t("main.file_not_image"), img_path)
                except OSError as e:
                    logging.info(t("main.exception"), img_path)
                    logging.info(e)
                finally:
                    pbar.update(1)
            pbar.set_postfix_str("")
            pbar.close()
    return os.EX_OK


def mirror_concat_file(file_path: str):
    """
    Попытка отзеркаливания одного изображения без обработки исключений.
    :param file_path: Путь к файлу.
    """
    return mirror_concat_img(PIL.Image.open(file_path))


if __name__ == "__main__":
    sys.tracebacklimit = 0
    prepare_app("images/Pillows_Hat_Icon.tga")
    parser = argparse.ArgumentParser(prog=t("main.mirror_concat_img_name"),
                                     description=t("main.mirror_concat_img_name"))
    parser.add_argument("img_paths", nargs="*", default=[], help=t("main.image_files"))
    args = parser.parse_args()
    sys.exit(execute_mirror_concat(askopenfilenames(title=t("main.select_image_files"), filetypes=[(
        t("main.image_files"), ["*" + ext for ext in SUPPORTED_EXTENSIONS])]) if len(
        args.img_paths) < 1 else args.img_paths))
