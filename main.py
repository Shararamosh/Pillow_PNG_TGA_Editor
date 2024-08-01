from helper_funcs import *
from tqdm import tqdm
from tkinter import filedialog
from tqdm.contrib.logging import logging_redirect_tqdm

if __name__ == "__main__":
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    supported_extensions = set(PIL.Image.registered_extensions().keys())
    root_path = filedialog.askdirectory()
    if root_path == "":
        exit()
    resave_success = 0
    error_files = []  # Файлы, которые не удалось прочитать.
    obsolete_files = []  # Файлы, которые необходимо удалить.
    already_exist_files = []  # Файлы, которые не удалось пересохранить, т.к.по новому пути уже существует другой файл.
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
                            logging.info(file_path_short + " -> " + new_file_path[len(root_path) + 1:])
                            if file_path not in obsolete_files:
                                obsolete_files.append(file_path)
                            if new_file_path in obsolete_files:
                                obsolete_files.remove(new_file_path)
                            resave_success += 1
            except Exception as e:
                if e == PIL.UnidentifiedImageError:
                    pbar.clear()
                    logging.info("Файл " + file_path_short + " не распознан как изображение.")
                else:
                    pbar.clear()
                    logging.info("Исключение для " + file_path_short + ":")
                    logging.info(e)
                error_files.append(file_path)
            pbar.update(os.stat(file_path).st_size)
        pbar.set_postfix_str("")
        pbar.close()
    if len(error_files) > 0:
        logging.info("Не удалось открыть файлы:")
        for error_file in error_files:
            logging.info(os.path.relpath(error_file, root_path))
    if resave_success > 0:
        logging.info("Удачно пересохранено файлов: " + str(resave_success) + ".")
    if len(already_exist_files) > 0:
        logging.info("Не удалось пересохранить файлы:")
        for already_exist_file in already_exist_files:
            logging.info(os.path.relpath(already_exist_file, root_path))
    if len(obsolete_files) > 0:
        logging.info("Следующие файлы будут удалены:")
        for obsolete_file in obsolete_files:
            logging.info(os.path.relpath(obsolete_file, root_path))
        for obsolete_file in obsolete_files:
            try:
                os.remove(obsolete_file)
            except Exception as e:
                logging.info("Исключение при удалении " + os.path.relpath(obsolete_file, root_path) + ":")
                logging.info(e)
