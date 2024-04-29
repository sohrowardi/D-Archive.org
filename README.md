# D-archive.org.py

This Python script allows you to download books from the Internet Archive (archive.org) and save them as PDFs or individual JPEGs.

## Features

- Download books from archive.org as PDFs or individual JPEGs.
- Multithreaded downloading for faster performance.
- Command-line interface with various options for customization.
- Handles errors and retries failed downloads.
- Can output the metadata of the book to a JSON file.

## Dependencies

The script requires the following Python libraries:

- `requests`
- `random`
- `string`
- `concurrent.futures`
- `tqdm`
- `time`
- `argparse`
- `os`
- `json`
- `queue`

You can install these with pip:

```bash
pip install -r requirements.txt
```

## Usage
You can run the script from the command line with the following options:
```bash
python D-archive.org.py -e <email> -p <password> -u <url> -d <dir> -f <file> -r <resolution> -t <threads> -j -m
```  
- `-e`, -`-email`: Your archive.org email (required).
- `-p`, -`-password`: Your archive.org password (required).
- `-u`, -`-url`: Link to the book (e.g., `https://archive.org/details/XXXX`). You can use this argument several times to download multiple books.
- `-d`, -`-dir`: Output directory.
- `-f`, -`-file`: File where the URLs of the books to download are stored.
- `-r`, -`-resolution`: Image resolution (10 to 0, 0 is the highest), default is 3.
- -`t`, -`-threads`: Maximum number of threads, default is 50.
- `-j`, --`jpg`: Output to individual JPGs rather than a PDF.
- `-m`, -`-meta`: Output the metadata of the book to a JSON file (-j option required).

## Example
```bash
python D-archive.org.py -e example@example.com -p password -u https://archive.org/details/book1 -u https://archive.org/details/book2 -d /path/to/output -r 2 -t 10 -j -m
```

This will download the books at the specified URLs from archive.org using the provided email and password, save the individual pages as JPEGs in the specified output directory, use a resolution of 2, use 10 threads for downloading, and output the metadata of the books to JSON files.

## Disclaimer
Please ensure that you have the necessary permissions to download and use the books, and comply with the terms of use of archive.org and any copyright laws applicable in your jurisdiction. This script is provided for educational purposes and does not endorse or encourage any illegal activity.

## Contact
For any issues or suggestions, please visit my GitHub page.
Feel free to customize this README for your specific project! 😊