from typing import List, Dict, Any
import os

from requests import cookies as rcookies, get as rget


def file(cookies: List[Dict[str, Any]], url: str, dir: str) -> None:
    """Download file with the help of additional cookies.

    Args:
        cookies (List[Dict[str, Any]]): list of cookie dictionary data
            e.g.:
                [{'domain': '.dijnet.hu',
                  'expiry': 1596773024,
                  'httpOnly': False,
                  'name': '_gid',
                  'path': '/',
                  'sameSite': 'None',
                  'secure': False,
                  'value': 'GA1.2.923094295.1596686625'}]
        url (str):
        dir (str):

    Returns:
        None
    """
    cookies_jar = rcookies.RequestsCookieJar()
    for cookie in cookies:
        cookies_jar.set(
            name=cookie["name"],
            value=cookie["value"],
            domain=cookie.get("domain", ""),
            path=cookie.get("path", ""),
        )

    r = rget(url, cookies=cookies_jar)
    if not r.ok:
        return "", 0

    basedir = os.path.join(os.getcwd(), dir)
    os.makedirs(basedir, exist_ok=True)
    filename = os.path.join(
        basedir, r.headers["Content-Disposition"].replace("attachment;filename=", ""),
    )

    with open(filename, "wb") as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
