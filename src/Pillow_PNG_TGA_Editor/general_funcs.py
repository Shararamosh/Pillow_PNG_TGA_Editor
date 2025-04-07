"""
    Скрипт с вспомогательными функциями для приложений.
"""
import os
import sys
import logging
import locale
import warnings
from tkinter import Tk

import i18n
import PIL.Image
import PIL.ImageTk

SUPPORTED_EXTENSIONS = set(PIL.Image.registered_extensions().keys())


def get_resource_path(file_path: str) -> str:
    """
    Получение пути к файлу или директории внутри проекта, если используется PyInstaller или Nuitka.
    :param file_path: Изначальный путь к файлу или директории.
    :return: Изменённый путь к файлу или директории.
    """
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        base_path = os.path.dirname(sys.executable)
    elif hasattr(sys, "_MEIPASS"):
        base_path = getattr(sys, "_MEIPASS")
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, file_path)


def init_app(icon_path: str):
    """
    Подготовка приложения к выполнению.
    :param icon_path: Путь к иконке для диалоговых окон Tkinter.
    """
    sys.tracebacklimit = 0
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
    root = Tk()
    root.withdraw()
    root.iconphoto(True, PIL.ImageTk.PhotoImage(file=get_resource_path(icon_path)))
