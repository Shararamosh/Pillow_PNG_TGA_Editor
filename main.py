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
import i18n
import PIL.Image
import PIL.ImageTk
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from helper_funcs import resave_img  # pylint: disable=import-error

logging.basicConfig(stream=sys.stdout, format="%(message)s", level=logging.INFO)
warnings.filterwarnings("ignore", category=DeprecationWarning)
i18n.set("locale", locale.getdefaultlocale()[0])  # pylint: disable=deprecated-method
i18n.set("fallback", "en_US")
i18n.load_path.append("localization")
i18n.set("file_format", "yml")
i18n.set("filename_format", "{namespace}.{format}")
i18n.set("skip_locale_root_data", True)
i18n.set("use_locale_dirs", True)
supported_extensions = set(PIL.Image.registered_extensions().keys())
if os.path.isfile("images/Pillows_Hat_Icon.tga"):
    root = Tk()
    root.withdraw()
    root.iconphoto(True, PIL.ImageTk.PhotoImage(file="images/Pillows_Hat_Icon.tga"))


def get_convertable_files(root_path: str) -> (list[str], int):
    """
    Получение списка путей к конвертируемым файлов.
    :param root_path: Путь к корневой директории.
    :return: Список путей к файлам и общий размер файлов.
    """
    all_files = []
    full_size = 0
    logging.info(i18n.t("main.indexing_start"))
    for subdir, _, files in os.walk(root_path):
        for file in files:
            file_path = os.path.abspath(os.path.join(subdir, file))
            if os.path.splitext(file_path)[1].lower() not in supported_extensions:
                continue
            all_files.append(file_path)  # Полный путь к файлу.
            full_size += os.stat(file_path).st_size
    logging.info(i18n.t("main.indexing_stop"))
    return all_files, full_size


def batch_convert_files(root_path: str, files: list[str], full_size: int) -> list[str]:
    """
    Конвертация изображений в нужный формат при соблюдении условий.
    :param root_path: Корневой путь к директории (для вычисления относительного пути к файлу).
    :param files: Список путей к изображениям.
    :param full_size: Полный размер всех изображений в списке.
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
        for file_path in files:
            file_path_rel = os.path.relpath(file_path, root_path)
            pbar.set_postfix_str(file_path_rel)
            try:
                with PIL.Image.open(file_path) as img:
                    try:
                        new_file_path = resave_img(img)
                    except OSError as e:
                        if e == FileExistsError:
                            already_exist_files.append(file_path)
                    else:
                        if new_file_path != "":
                            pbar.clear()
                            logging.info("%s -> %s", file_path_rel,
                                         new_file_path[len(root_path) + 1:])
                            if file_path not in obsolete_files:
                                obsolete_files.append(file_path)
                            if new_file_path in obsolete_files:
                                obsolete_files.remove(new_file_path)
                            resave_success += 1
            except OSError as e:
                if e == PIL.UnidentifiedImageError:
                    pbar.clear()
                    logging.info(i18n.t("main.file_not_image"), file_path_rel)
                else:
                    pbar.clear()
                    logging.info(i18n.t("main.exception"), file_path_rel)
                    logging.info(e)
                error_files.append(file_path)
            pbar.update(os.stat(file_path).st_size)
        pbar.set_postfix_str("")
        pbar.close()
    log_statistics(root_path, error_files, resave_success, already_exist_files, obsolete_files)
    return obsolete_files


def batch_remove_files(root_path: str, files: list[str]):
    """
    Удаление файлов.
    :param root_path: Корневой путь к директории (для вычисления относительного пути к файлу).
    :param files: Список путей к файлам.
    """
    for file in files:
        try:
            os.remove(file)
        except OSError as e:
            logging.info(i18n.t("main.exception_remove"), os.path.relpath(file, root_path))
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
    obsolete_files = batch_convert_files(root_path, all_files, full_size)
    batch_remove_files(root_path, obsolete_files)
    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
