"""
    Скрипт, конвертирующий изображения в заданной директории из форматов, поддерживаемых библиотекой
    Pillow в форматы, читаемые A Hat in Time/Unreal Engine 3 Editor.
"""
import os
import sys
import logging
from tkinter import filedialog
import PIL.Image
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from helper_funcs import resave_img

logging.basicConfig(format="%(message)s", level=logging.INFO)


def main():
    """
    Конвертация изображения в заданной директории из форматов, поддерживаемых библиотекой Pillow
    в форматы, читаемые A Hat in Time/Unreal Engine 3 Editor.
    :return:
    """
    supported_extensions = set(PIL.Image.registered_extensions().keys())
    root_path = filedialog.askdirectory()
    if root_path == "":
        sys.exit()
    resave_success = 0
    error_files = []  # Файлы, которые не удалось прочитать.
    obsolete_files = []  # Файлы, которые необходимо удалить.
    already_exist_files = []  # Файлы, которые не удалось пересохранить, так как по новому пути
    # уже существует другой файл, совпадающий по имени и расширению с конвертированным.
    all_files = []  # Все файлы в корневой директории.
    full_size = 0
    for subdir, _, files in os.walk(root_path):
        for file in files:
            file_path = os.path.join(subdir, file)
            if os.path.splitext(file_path)[1].lower() not in supported_extensions:
                continue
            all_files.append(file_path)  # Полный путь к файлу.
            full_size += os.stat(file_path).st_size
    with logging_redirect_tqdm():
        pbar = tqdm(total=full_size, position=0, unit="B", unit_scale=True, desc="Файлы")
        for file_path in all_files:
            file_path_short = os.path.relpath(file_path, root_path)
            pbar.set_postfix_str(file_path_short)
            try:
                with PIL.Image.open(file_path) as img:
                    try:
                        new_file_path = resave_img(img)
                    except Exception as e:
                        if e == FileExistsError:
                            already_exist_files.append(file_path)
                    else:
                        if new_file_path != "":
                            pbar.clear()
                            logging.info("%s -> %s", file_path_short,
                                         new_file_path[len(root_path) + 1:])
                            if file_path not in obsolete_files:
                                obsolete_files.append(file_path)
                            if new_file_path in obsolete_files:
                                obsolete_files.remove(new_file_path)
                            resave_success += 1
            except Exception as e:
                if e == PIL.UnidentifiedImageError:
                    pbar.clear()
                    logging.info("Файл %s не распознан как изображение.", file_path_short)
                else:
                    pbar.clear()
                    logging.info("Исключение для %s:", file_path_short)
                    logging.info(e)
                error_files.append(file_path)
            pbar.update(os.stat(file_path).st_size)
        pbar.set_postfix_str("")
        pbar.close()
    log_statistics(root_path, error_files, resave_success, already_exist_files, obsolete_files)
    for obsolete_file in obsolete_files:
        try:
            os.remove(obsolete_file)
        except Exception as e:
            logging.info("Исключение при удалении %s:", os.path.relpath(obsolete_file, root_path))
            logging.info(e)


def log_statistics(root_path: str, error_files: list[str], resave_success: int,
                   already_exist_files: list[str], obsolete_files: list[str]):
    """
    Печать статистики после прохода по файлам из директории.
    :param root_path: Путь к изначальной директории.
    :param error_files: Список с путями к файлам, к которым не удалось получить доступ.
    :param resave_success: Количество файлов, которые были конвертированы.
    :param already_exist_files: Список с путями к файлам, которые не удалось конвертировать, так как
        файл с новым путём уже существует.
    :param obsolete_files: Файлы, которые необходимо удалить после конвертации.
    :return:
    """
    if len(error_files) > 0:
        logging.info("Не удалось открыть файлы:")
        for error_file in error_files:
            logging.info(os.path.relpath(error_file, root_path))
    if resave_success > 0:
        logging.info("Удачно пересохранено файлов: %s.", resave_success)
    if len(already_exist_files) > 0:
        logging.info("Не удалось пересохранить файлы:")
        for already_exist_file in already_exist_files:
            logging.info(os.path.relpath(already_exist_file, root_path))
    if len(obsolete_files) > 0:
        logging.info("Следующие файлы будут удалены:")
        for obsolete_file in obsolete_files:
            logging.info(os.path.relpath(obsolete_file, root_path))


if __name__ == "__main__":
    main()
