import requests
import random
import string
from concurrent import futures
from tqdm import tqdm
import time
import argparse
import os
import json
from queue import Queue


def display_error(response, message):
    error_message = f"{message}\n{response}\n{response.text}"
    raise RuntimeError(error_message)


def get_book_infos(session, url):
    try:
        # Fetch initial response
        initial_response = session.get(url)
        initial_response.raise_for_status()  # Raise exception for HTTP errors
        initial_data = initial_response.json()
        
        # Extract information
        infos_url = "https:" + initial_data.get("url")
        response = session.get(infos_url)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()['data']

        # Extract title
        title = data['brOptions']['bookTitle'].strip().replace(" ", "_")
        title = ''.join(c for c in title if c not in '<>:"/\\|?*')[:150]  # Trim and filter forbidden chars

        # Extract metadata
        metadata = data.get('metadata', {})

        # Extract links
        links = [page['uri'] for item in data.get('brOptions', {}).get('data', []) for page in item]

        if len(links) > 1:
            print(f"[+] Found {len(links)} pages")
            return title, links, metadata
        else:
            raise ValueError("[-] Error: Unable to retrieve image links")
    except (requests.RequestException, ValueError) as e:
        print(f"[-] Error: {e}")
        exit()


def format_data(content_type, fields):
    data = [f"--{content_type}\x0d\x0aContent-Disposition: form-data; name=\"{name}\"\x0d\x0a\x0d\x0a{value}\x0d\x0a"
            for name, value in fields.items()]
    return ''.join(data) + content_type + '--'


def login(email, password):
    session = requests.Session()
    session.get("https://archive.org/account/login")
    content_type = "----WebKitFormBoundary"+"".join(random.sample(string.ascii_letters + string.digits, 16))

    headers = {'Content-Type': 'multipart/form-data; boundary='+content_type}
    data = format_data(content_type, {"username":email, "password":password, "submit_by_js":"true"})

    response = session.post("https://archive.org/account/login", data=data, headers=headers)
    if "bad_login" in response.text:
        raise ValueError("Invalid credentials!")
    elif "Successful login" in response.text:
        print("[+] Successful login")
        return session
    else:
        display_error(response, "[-] Error while login:")


def loan(session, book_id, verbose=True):
    data = {
        "action": "grant_access",
        "identifier": book_id
    }
    response = session.post("https://archive.org/services/loans/loan/", data=data)

    if response.status_code == 400:
        error_message = response.json().get("error", "")
        if error_message == "This book is not available to borrow at this time. Please try again later.":
            print("This book doesn't need to be borrowed")
            return session
        else:
            raise RuntimeError("Something went wrong when trying to borrow the book.")

    if "token" in response.text:
        if verbose:
            print("[+] Successful loan")
        return session
    else:
        raise RuntimeError("Something went wrong when trying to borrow the book, maybe you can't borrow this book.")

def return_loan(session, book_id):
    data = {
        "action": "return_loan",
        "identifier": book_id
    }
    response = session.post("https://archive.org/services/loans/loan/", data=data)

    if response.status_code == 200:
        success = response.json().get("success", False)
        if success:
            print("[+] Book returned")
            return
    raise RuntimeError("Something went wrong when trying to return the book")


def image_name(pages, page, directory):
    if not isinstance(pages, int) or not isinstance(page, int) or pages <= 0 or page <= 0:
        raise ValueError("Invalid values for pages and page")
    
    return f"{directory}/{(len(str(pages)) - len(str(page))) * '0'}{page}.jpg"


def download_one_image(session, link, i, directory, book_id, pages, max_retries=3):
    headers = {
        "Referer": "https://archive.org/",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "image",
    }
    retries = 0
    while retries < max_retries:
        try:
            response = session.get(link, headers=headers)
            response.raise_for_status()  # Raise exception for HTTP errors
            if response.status_code == 403:
                session = loan(session, book_id, verbose=False)
                raise RuntimeError("Borrow again")
            elif response.status_code == 200:
                break  # Successful response, exit loop
        except requests.exceptions.RequestException as e:
            retries += 1
            if retries == max_retries:
                raise RuntimeError(f"Failed to download image after {max_retries} retries: {e}")
            time.sleep(1)  # Wait before retrying
    
    # Construct image file name
    image = image_name(pages, i, directory)
    
    # Write image content to file
    with open(image, "wb") as f:
        f.write(response.content)


def download(session, n_threads, directory, links, scale, book_id):
    print("Downloading pages...")
    links = [f"{link}&rotate=0&scale={scale}" for link in links]
    pages = len(links)
    images = []

    def download_task(link, i):
        nonlocal images
        try:
            download_one_image(session=session, link=link, i=i, directory=directory, book_id=book_id, pages=pages)
            images.append(image_name(pages, i, directory))
        except Exception as e:
            print(f"Error downloading image {i}: {e}")

    tasks_queue = Queue()
    for i, link in enumerate(links):
        tasks_queue.put((link, i))

    with futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures_list = [executor.submit(download_task, link, i) for link, i in iter(tasks_queue.get, None)]

        for future in tqdm(futures.as_completed(futures_list), total=len(links)):
            pass

    return images


def make_pdf(pdf, title, directory):
    file = title + ".pdf"
    i = 1
    while os.path.isfile(os.path.join(directory, file)):
        file = f"{title}({i}).pdf"
        i += 1

    try:
        with open(os.path.join(directory, file), "wb") as f:
            f.write(pdf)
        print(f"[+] PDF saved as \"{file}\"")
    except Exception as e:
        print(f"[-] Error saving PDF: {e}")



def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--email', help='Your archive.org email', type=str, required=True)
    parser.add_argument('-p', '--password', help='Your archive.org password', type=str, required=True)
    parser.add_argument('-u', '--url', help='Link to the book (https://archive.org/details/XXXX). You can use this argument several times to download multiple books', action='append', type=str)
    parser.add_argument('-d', '--dir', help='Output directory', type=str)
    parser.add_argument('-f', '--file', help='File where are stored the URLs of the books to download', type=str)
    parser.add_argument('-r', '--resolution', help='Image resolution (10 to 0, 0 is the highest), [default 3]', type=int, default=3)
    parser.add_argument('-t', '--threads', help="Maximum number of threads, [default 50]", type=int, default=50)
    parser.add_argument('-j', '--jpg', help="Output to individual JPG's rather than a PDF", action='store_true')
    parser.add_argument('-m', '--meta', help="Output the metadata of the book to a json file (-j option required)", action='store_true')
    return parser.parse_args()

def validate_arguments(args):
    if args.url is None and args.file is None:
        raise ValueError("At least one of --url and --file required")

    if args.dir is None:
        args.dir = os.getcwd()
    elif not os.path.isdir(args.dir):
        raise ValueError("Output directory does not exist!")

def main():
    args = parse_arguments()
    validate_arguments(args)

    if args.url is not None:
        urls = args.url
    else:
        if os.path.exists(args.file):
            with open(args.file) as f:
                urls = f.read().strip().split("\n")
        else:
            raise FileNotFoundError(f"{args.file} does not exist!")

    # Check the urls format
    for url in urls:
        if not url.startswith("https://archive.org/details/"):
            raise ValueError(f"{url} --> Invalid url. URL must start with \"https://archive.org/details/\"")

    print(f"{len(urls)} Book(s) to download")

    session = login(args.email, args.password)

    for url in urls:
        book_id = list(filter(None, url.split("/")))[3]
        print("=" * 40)
        print(f"Current book: https://archive.org/details/{book_id}")

        session = loan(session, book_id)
        title, links, metadata = get_book_infos(session, url)

        directory = os.path.join(args.dir, title)
        # Handle the case where multiple books with the same name are downloaded
        i = 1
        _directory = directory
        while os.path.isdir(directory):
            directory = f"{_directory}({i})"
            i += 1
        os.makedirs(directory)

        if args.meta:
            print("Writing metadata.json...")
            with open(f"{directory}/metadata.json", 'w') as f:
                json.dump(metadata, f)

        images = download(session, args.threads, directory, links, args.resolution, book_id)

        if not args.jpg:
            # Create PDF with images and remove the images folder
            make_pdf(images, title, args.dir if args.dir != None else "")

        return_loan(session, book_id)

if __name__ == "__main__":
    main()
