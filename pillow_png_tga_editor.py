"""
    Скрипт, конвертирующий изображения в заданной директории из форматов, поддерживаемых библиотекой
    PIL (Pillow) в форматы, читаемые Unreal Engine.
"""
# pylint: disable=import-error, line-too-long
import os
import sys
import argparse
import logging
from tkinter.filedialog import askdirectory
from concurrent.futures import ThreadPoolExecutor, as_completed
from i18n import t
import PIL.Image
import PIL.ImageTk
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from main import init_app, SUPPORTED_EXTENSIONS
from helper_funcs import resave_img


def get_convertable_files(root_path: str) -> list[str]:
    """
    Получение списка путей к конвертируемым файлов.
    :param root_path: Путь к корневой директории.
    :return: Список путей к файлам.
    """
    file_paths = []
    logging.info(t("main.indexing_start"))
    for subdir, _, files in os.walk(root_path):
        for file in files:
            file_path = os.path.abspath(os.path.join(subdir, file))
            if os.path.splitext(file_path)[1].lower() not in SUPPORTED_EXTENSIONS:
                continue
            file_paths.append(file_path)
    logging.info(t("main.indexing_stop"))
    return file_paths


def batch_convert_files(root_path: str, file_paths: list[str]) -> list[
    str]:
    """
    Конвертация изображений в нужный формат при соблюдении условий.
    :param root_path: Корневой путь к директории (для вычисления относительного пути к файлу).
    :param file_paths: Список путей к файлам.
    :return: Список путей к изображениям, которые нужно удалить.
    """
    resave_success = 0  # Количество изображений, которые успешно конвертированы.
    error_files = []  # Файлы, которые не удалось прочитать.
    obsolete_files = []  # Файлы, которые необходимо удалить.
    already_exist_files = []  # Файлы, которые не удалось конвертировать, так как по новому пути
    # уже существует другой файл, совпадающий по имени и расширению с конвертированным.
    with logging_redirect_tqdm():
        pbar = tqdm(total=len(file_paths), desc=t("main.files"))
        with ThreadPoolExecutor() as executor:
            future_convert_file = {executor.submit(convert_file, file_path): file_path for
                                   file_path in file_paths}
            for future in as_completed(future_convert_file):
                file_path = future_convert_file[future]
                file_path_rel = os.path.relpath(file_path, root_path)
                pbar.set_postfix_str(file_path_rel)
                try:
                    new_file_path = future.result()
                except PIL.UnidentifiedImageError:
                    error_files.append(file_path)
                    logging.info(t("main.file_not_image"),
                                 os.path.relpath(file_path, root_path))
                except FileExistsError as e:
                    already_exist_files.append(file_path)
                    logging.info(e)
                except OSError as e:
                    logging.info(t("main.exception"), file_path_rel)
                    logging.info(e)
                else:
                    if new_file_path != "":
                        logging.info("%s -> %s", file_path_rel, new_file_path[len(root_path) + 1:])
                        if file_path not in obsolete_files:
                            obsolete_files.append(file_path)
                        if new_file_path in obsolete_files:
                            obsolete_files.remove(new_file_path)
                        if new_file_path in error_files:
                            error_files.remove(new_file_path)
                        resave_success += 1
                finally:
                    pbar.update(1)
        pbar.set_postfix_str("")
        pbar.close()
    log_statistics(root_path, error_files, resave_success, already_exist_files, obsolete_files)
    return obsolete_files


def convert_file(file_path: str) -> str:
    """
    Попытка открытия и конвертирования одного изображения без обработки исключений.
    :param file_path: Путь к файлу.
    :return: Новый путь к файлу, если файл был удачно конвертирован или тот же, если файл был просто
        пересохранён, а иначе - пустая строка.
    """
    return resave_img(PIL.Image.open(file_path))


def batch_remove_files(root_path: str, file_paths: list[str]):
    """
    Удаление файлов.
    :param root_path: Корневой путь к директории (для вычисления относительного пути к файлу).
    :param file_paths: Список путей к файлам.
    """
    with ThreadPoolExecutor() as executor:
        future_remove_file = {executor.submit(remove_wrapper, file_path): file_path for file_path in
                              file_paths}
    for future in as_completed(future_remove_file):
        file_path = future_remove_file[future]
        try:
            future.result()
        except OSError as e:
            logging.info(t("main.exception_remove"), os.path.relpath(file_path, root_path))
            logging.info(e)


def remove_wrapper(file_path: str):
    """
    Обёртка для функции os.remove, чтобы Pylint не ругался.
    :param file_path: Путь к файлу.
    """
    os.remove(file_path)


def log_statistics(root_path: str, error_files: list[str], resave_success: int,
                   already_exist_files: list[str], obsolete_files: list[str]):
    """
    Печать статистики после прохода по файлам из директории.
    :param root_path: Путь к изначальной директории.
    :param error_files: Список с путями к файлам, к которым не удалось получить доступ.
    :param resave_success: Количество файлов, которые были конвертированы.
    :param already_exist_files: Список с путями к файлам, которые не удалось конвертировать, так как файл с новым путём уже существует.
    :param obsolete_files: Файлы, которые необходимо удалить после конвертации.
    """
    if len(error_files) > 0:
        logging.info(t("main.failed_to_open_files"))
        for error_file in error_files:
            logging.info(os.path.relpath(error_file, root_path))
    if resave_success > 0:
        logging.info(t("main.converted_files"), resave_success)
    if len(already_exist_files) > 0:
        logging.info(t("main.failed_to_convert_files"))
        for already_exist_file in already_exist_files:
            logging.info(os.path.relpath(already_exist_file, root_path))
    if len(obsolete_files) > 0:
        logging.info(t("main.pending_removal_files"))
        for obsolete_file in obsolete_files:
            logging.info(os.path.relpath(obsolete_file, root_path))


def execute_convert(root_path) -> str | int:
    """
    Конвертация изображения в заданной директории из форматов, поддерживаемых библиотекой Pillow
    в форматы, читаемые Unreal Engine.
    :return: Код ошибки или строка с ошибкой.
    """
    if root_path == "" or not os.path.isdir(root_path):
        if sys.platform == "win32":
            return 144  # ERROR_DIR_NOT_ROOT
        return os.EX_OK
    file_paths = get_convertable_files(root_path)
    obsolete_files = batch_convert_files(root_path, file_paths)
    batch_remove_files(root_path, obsolete_files)
    return os.EX_OK


if __name__ == "__main__":
    init_app("images/Pillows_Hat_Icon.tga")
    parser = argparse.ArgumentParser(prog=t("main.pillow_png_tga_editor_name"),
                                     description=t("main.pillow_png_tga_editor_desc"))
    parser.add_argument("input_path", nargs="?", type=str, default="",
                        help=t("main.input_path_arg"))
    args = parser.parse_args()
    sys.exit(execute_convert(args.input_path if args.input_path != "" else askdirectory()))
