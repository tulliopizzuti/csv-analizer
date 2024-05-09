import argparse
import pandas as pd
from pathlib import Path
import zipfile
import os
import math


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def zip_information_extraction(file, extension, original_file=None):
    print(f'Opening ZIP: {file}')
    res = []
    try:
        archive = zipfile.ZipFile(file, 'r')
        csv_files=[]
        for ext in extension:
            csv_files.extend(list(filter(lambda name: '__MACOSX' not in name and name.endswith(ext), archive.namelist())))
        zip_files = (list(filter(lambda name: '__MACOSX' not in name and name.endswith('.zip'), archive.namelist())))
        for csv in csv_files:
            res.append(csv_information_extraction(archive.open(csv),
                                                  os.path.join(
                                                      archive.filename) if original_file == None else original_file,
                                                  str(csv), convert_size(archive.getinfo(csv).file_size)))

        for zip in zip_files:
            res.extend(zip_information_extraction(archive.open(zip),extension, os.path.join(archive.filename) + "\\" + str(
                zip) if original_file == None else original_file + "\\" + str(zip)))
    except zipfile.BadZipFile:
        print(f'Error opening ZIP: {file}')
    return res


def csv_information_extraction(file, path, filename, size='0MB'):
    print(f'CSV Information extraction: {path} # {filename}')
    try:

        df = pd.read_csv(file, iterator=True, keep_default_na=False, sep=None, header=None, engine='python')
        delimiter = df._engine.data.dialect.delimiter
        df = df.read()

        null_chars = ['', '?']
        founded_null_chars = []
        for char in null_chars:
            if char in df.values:
                founded_null_chars.append(char if char != '' else 'blank')

        columns = len(df.columns)
        rows = len(df)
        initial_type = df.dtypes
        if type(file) is zipfile.ZipExtFile:
            file.seek(0)
        df = pd.read_csv(file, delimiter=delimiter)
        types_without_first_row = df.dtypes
        probably_header = list(initial_type) != list(types_without_first_row)
        types = set(map(lambda x:str(x),list(types_without_first_row)))


        return {
            "path": path,
            "file": filename,
            "columns": columns,
            "rows": rows,
            "delimiter": delimiter,
            "null_char": None if len(founded_null_chars) == 0 else ", ".join(founded_null_chars),
            "size": size,
            "probably_header": probably_header,
            "types": types

        }
    except Exception as e:
        print(f'ERROR on CSV Information extraction: {path} # {filename}')
        return {
            "path": path,
            "file": filename,
            "columns": 0,
            "rows": 0,
            "delimiter": None,
            "null_char": None
        }


parser = argparse.ArgumentParser(
    prog='csv-analizer.py',
    description='Extract information from CSV files.')

parser.add_argument('input', help="Input CSV file or directory.")
parser.add_argument('-o', '--output', help="Output CSV file.", type=str, default="result.csv")
parser.add_argument('-c', '--explore_compress_file', help='Search CSV in compress files (if input is a directory).', action=argparse.BooleanOptionalAction)
parser.add_argument('-e', '--extensions', help='Comma separated extensions of CSV, default=[.csv, .data].',type=str, default=".csv, .data")

args = parser.parse_args()
input_arg = args.input
output = args.output
explore_compress_file = args.explore_compress_file
extensions=args.extensions.replace(', ',',').split(',')
input = Path(input_arg)
result = []
if input.is_dir():
    search_stategy = '**/'
    csv_files=[]
    for ext in extensions:
        csv_files.extend(list(input.glob(search_stategy + f'*{ext}')))
    zip_files = list(input.glob(search_stategy + '*.zip'))
    for csv in csv_files:
        result.append(csv_information_extraction(csv, input_arg, csv, convert_size(os.path.getsize(csv))))
    if explore_compress_file:
        for zip_file in zip_files:
            result.extend(zip_information_extraction(zip_file, extensions))
elif input.is_file():
    suffix = ''.join(input.suffixes)
    if suffix == '.csv':
        result.append(csv_information_extraction(input, input.cwd(), str(input)))
    elif suffix == '.zip':
        result.extend(zip_information_extraction(input))
    else:
        print("Unknown file type")
else:
    print("Error on input")
    exit(0)

result = pd.DataFrame.from_dict(result)
result['columns'] = result['columns'].astype(int)
result['rows'] = result['rows'].astype(int)
result.to_csv(output, index=False)
