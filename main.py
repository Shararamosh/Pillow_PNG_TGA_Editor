"""
    Скрипт, конвертирующий изображения в заданной директории из форматов, поддерживаемых библиотекой
    Pillow в форматы, читаемые A Hat in Time/Unreal Engine 3 Editor.
"""
import os
import sys
import logging
import locale
import warnings
from tkinter import Tk, filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
import i18n
import PIL.Image
import PIL.ImageTk
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from helper_funcs import resave_img  # pylint: disable=import-error

USE_CONCURRENT = True


def get_resource_path(filename: str) -> str:
    """
    Получение пути к файлу или директории, если используется PyInstaller.
    :param filename: Изначальный путь к файлу или директории.
    :return: Изменённый путь к файлу или директории.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(getattr(sys, "_MEIPASS"), filename)
    return filename


logging.basicConfig(stream=sys.stdout, format="%(message)s", level=logging.INFO)
warnings.filterwarnings("ignore", category=DeprecationWarning)
# noinspection PyDeprecation
i18n.set("locale", locale.getdefaultlocale()[0])  # pylint: disable=deprecated-method
i18n.set("fallback", "en_US")
i18n.load_path.append(get_resource_path("localization"))
i18n.set("file_format", "yml")
i18n.set("filename_format", "{namespace}.{format}")
i18n.set("skip_locale_root_data", True)
i18n.set("use_locale_dirs", True)
supported_extensions = set(PIL.Image.registered_extensions().keys())
root = Tk()
root.withdraw()
root.iconphoto(True, PIL.ImageTk.PhotoImage(file=get_resource_path("images/Pillows_Hat_Icon.tga")))


def get_convertable_files(root_path: str) -> (list[tuple[str, int]], int):
    """
    Получение списка путей к конвертируемым файлов.
    :param root_path: Путь к корневой директории.
    :return: Список из кортежа (путь к файлу, размер файла) и общий размер файлов.
    """
    all_files = []
    full_size = 0
    logging.info(i18n.t("main.indexing_start"))
    for subdir, _, files in os.walk(root_path):
        for file in files:
            file_path = os.path.abspath(os.path.join(subdir, file))
            if os.path.splitext(file_path)[1].lower() not in supported_extensions:
                continue
            file_size = os.stat(file_path).st_size
            all_files.append((file_path, file_size))
            full_size += file_size
    logging.info(i18n.t("main.indexing_stop"))
    return all_files, full_size


def batch_convert_files(root_path: str, file_tuples: list[tuple[str, int]], full_size: int,
                        use_concurrent: bool) -> list[str]:
    """
    Конвертация изображений в нужный формат при соблюдении условий.
    :param root_path: Корневой путь к директории (для вычисления относительного пути к файлу).
    :param file_tuples: Список кортежей из двух элементов - путь к файлу и размер файла в байтах.
    :param full_size: Полный размер всех изображений в списке.
    :param use_concurrent: Использовать асинхронные вызовы из concurrent.
    :return: Список путей к изображениям, которые нужно удалить.
    """
    resave_success = 0  # Количество изображений, которые успешно конвертированы.
    error_files = []  # Файлы, которые не удалось прочитать.
    obsolete_files = []  # Файлы, которые необходимо удалить.
    already_exist_files = []  # Файлы, которые не удалось конвертировать, так как по новому пути
    # уже существует другой файл, совпадающий по имени и расширению с конвертированным.
    with logging_redirect_tqdm():
        pbar = tqdm(total=full_size, position=0, unit="B", unit_scale=True,
                    desc=i18n.t("main.files"))
        if use_concurrent:
            with ThreadPoolExecutor() as executor:
                future_convert_file = {executor.submit(convert_file, file_tuple[0]): file_tuple for
                                       file_tuple in file_tuples}
                for future in as_completed(future_convert_file):
                    file_tuple = future_convert_file[future]
                    file_path_rel = os.path.relpath(file_tuple[0], root_path)
                    pbar.set_postfix_str(file_path_rel)
                    try:
                        new_file_path = future.result()
                    except PIL.UnidentifiedImageError:
                        error_files.append(file_tuple[0])
                        logging.info(i18n.t("main.file_not_image"),
                                     os.path.relpath(file_tuple[0], root_path))
                    except FileExistsError:
                        already_exist_files.append(file_tuple[0])
                    except OSError as e:
                        logging.info(i18n.t("main.exception"), file_path_rel)
                        logging.info(e.strerror)
                    else:
                        if new_file_path != "":
                            logging.info("%s -> %s", file_path_rel,
                                         new_file_path[len(root_path) + 1:])
                            if file_tuple[0] not in obsolete_files:
                                obsolete_files.append(file_tuple[0])
                            if new_file_path in obsolete_files:
                                obsolete_files.remove(new_file_path)
                            if new_file_path in error_files:
                                error_files.remove(new_file_path)
                            resave_success += 1
                    finally:
                        pbar.update(file_tuple[1])
        else:
            for file_tuple in file_tuples:
                file_path_rel = os.path.relpath(file_tuple[0], root_path)
                pbar.set_postfix_str(file_path_rel)
                try:
                    new_file_path = convert_file(file_tuple[0])
                except PIL.UnidentifiedImageError:
                    error_files.append(file_tuple[0])
                    logging.info(i18n.t("main.file_not_image"),
                                 os.path.relpath(file_tuple[0], root_path))
                except FileExistsError:
                    already_exist_files.append(file_tuple[0])
                except OSError as e:
                    logging.info(i18n.t("main.exception"), file_path_rel)
                    logging.info(e.strerror)
                else:
                    if new_file_path != "":
                        logging.info("%s -> %s", file_path_rel, new_file_path[len(root_path) + 1:])
                        if file_tuple[0] not in obsolete_files:
                            obsolete_files.append(file_tuple[0])
                        if new_file_path in obsolete_files:
                            obsolete_files.remove(new_file_path)
                        if new_file_path in error_files:
                            error_files.remove(new_file_path)
                        resave_success += 1
                finally:
                    pbar.update(file_tuple[1])
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


def batch_remove_files(root_path: str, file_paths: list[str], use_concurrent: bool):
    """
    Удаление файлов.
    :param root_path: Корневой путь к директории (для вычисления относительного пути к файлу).
    :param file_paths: Список путей к файлам.
    :param use_concurrent: Использовать асинхронные вызовы из concurrent.
    """
    if use_concurrent:
        with ThreadPoolExecutor() as executor:
            future_remove_file = {executor.submit(remove_wrapper, file_path): file_path for
                                  file_path in file_paths}
        for future in as_completed(future_remove_file):
            file_path = future_remove_file[future]
            try:
                future.result()
            except OSError as e:
                logging.info(i18n.t("main.exception_remove"), os.path.relpath(file_path, root_path))
                logging.info(e)
    else:
        for file_path in file_paths:
            try:
                os.remove(file_path)
            except OSError as e:
                logging.info(i18n.t("main.exception_remove"), os.path.relpath(file_path, root_path))
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
    :param already_exist_files: Список с путями к файлам, которые не удалось конвертировать, так как
        файл с новым путём уже существует.
    :param obsolete_files: Файлы, которые необходимо удалить после конвертации.
    :return:
    """
    if len(error_files) > 0:
        logging.info(i18n.t("main.failed_to_open_files"))
        for error_file in error_files:
            logging.info(os.path.relpath(error_file, root_path))
    if resave_success > 0:
        logging.info(i18n.t("main.converted_files"), resave_success)
    if len(already_exist_files) > 0:
        logging.info(i18n.t("main.failed_to_convert_files"))
        for already_exist_file in already_exist_files:
            logging.info(os.path.relpath(already_exist_file, root_path))
    if len(obsolete_files) > 0:
        logging.info(i18n.t("main.pending_removal_files"))
        for obsolete_file in obsolete_files:
            logging.info(os.path.relpath(obsolete_file, root_path))


def main() -> str | int:
    """
    Конвертация изображения в заданной директории из форматов, поддерживаемых библиотекой Pillow
    в форматы, читаемые A Hat in Time/Unreal Engine 3 Editor.
    :return: Код ошибки или строка с ошибкой.
    """
    root_path = filedialog.askdirectory()
    if root_path == "":
        if sys.platform == "win32":
            return 144  # ERROR_DIR_NOT_ROOT
        return os.EX_OK
    all_files, full_size = get_convertable_files(root_path)
    obsolete_files = batch_convert_files(root_path, all_files, full_size, USE_CONCURRENT)
    batch_remove_files(root_path, obsolete_files, USE_CONCURRENT)
    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
