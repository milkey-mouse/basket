from urllib.parse import urlparse, urlunparse
from werkzeug.urls import url_decode, url_encode


def with_query_string(url, key, value):
    parsed = urlparse(url)
    query_string = url_decode(parsed.query)
    query_string[key] = value
    parsed = parsed._replace(query=url_encode(query_string))
    return urlunparse(parsed)
