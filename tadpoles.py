from json import loads, dumps
from datetime import datetime
import os

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from pytz import timezone
import requests

def write_all_bytes(path, contents):
    with open(path, "wb") as dest:
        dest.write(contents)

def write_all_text(path, contents):
    with open(path, "w") as dest:
        dest.write(contents)

def iter_events(browser):
    cursor = ""
    while True:
        browser.get(f"https://www.tadpoles.com/remote/v1/events?num_events=300&cursor={cursor}")
        resp = loads(browser.find_element_by_tag_name('pre').text)
        events = resp.get("events")
        cursor = resp.get("cursor")
        for event in events:
            yield event
        if cursor is None:
            break

def main():
    base_dir = os.path.dirname(__file__)
    output_dir = os.path.join(base_dir, "output")
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    opts = Options()
    browser = Chrome(options=opts)
    browser.get("https://www.tadpoles.com/home_or_work")
    WebDriverWait(browser, 600).until(lambda d: d.current_url == "https://www.tadpoles.com/parents")
    events = iter_events(browser)
    for event in events:
        new_attachments = event.get("new_attachments", list())
        event_key = event["key"]
        for attachment in new_attachments:
            attachment_key = attachment["key"]

            file_name_without_ext, ext = os.path.splitext(attachment["filename"])
            if attachment["mime_type"] == "image/jpeg" and ext == ".bin":
                attachment["filename"] = file_name_without_ext + ".jpg"

            tz = timezone(event["tz"])
            attachment_info = \
            {
                "mime_type": attachment["mime_type"],
                "filename": attachment["filename"],
                "members_display": event["members_display"],
                "comment": event["comment"],
                "event_date": event["event_date"],
                "location_display": event["location_display"],
                "event_time": datetime.fromtimestamp(event["event_time"], tz).isoformat(),
                "create_time": datetime.fromtimestamp(event["create_time"], tz).isoformat(),
                "labels": event.get("labels")
            }
            obj_file_path = os.path.join(output_dir, f'{event["event_date"]}_{attachment["filename"]}')
            if os.path.isfile(obj_file_path):
                print(f"skipping {obj_file_path}")
                continue
                
            attachment_uri = f"https://www.tadpoles.com/remote/v1/obj_attachment?obj={event_key}&key={attachment_key}"
            browser.get(attachment_uri)
            jar = requests.cookies.RequestsCookieJar()
            for cookie in browser.get_cookies():
                jar.set(cookie["name"], cookie["value"], path=cookie["path"])
            resp = requests.get(attachment_uri, cookies=jar)
            write_all_bytes(obj_file_path, resp.content)
            write_all_text(obj_file_path + ".json", dumps(attachment_info, sort_keys=True, indent=4))

if __name__ == "__main__":
    main()