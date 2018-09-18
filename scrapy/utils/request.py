"""
This module provides some useful functions for working with
scrapy.http.Request objects
"""

from __future__ import print_function
import hashlib
import weakref
from six.moves.urllib.parse import urlunparse

from w3lib.http import basic_auth_header
from scrapy.utils.python import to_bytes, to_native_str

from w3lib.url import canonicalize_url
from scrapy.utils.httpobj import urlparse_cached

# 使用了python的弱引用，保存指纹
_fingerprint_cache = weakref.WeakKeyDictionary()
def request_fingerprint(request, include_headers=None):
    """
    Return the request fingerprint.
    返回请求的指纹

    The request fingerprint is a hash that uniquely identifies the resource the
    request points to. For example, take the following two urls:
    请求指纹是一个哈希，唯一的标识请求指向的资源。比如下面2个url：

    http://www.example.com/query?id=111&cat=222
    http://www.example.com/query?cat=222&id=111

    Even though those are two different URLs both point to the same resource
    and are equivalent (ie. they should return the same response).
    即使这些是2个不同的url同时指向相同的资源，并且是相等的。(他们应该返回同样的资源)

    Another example are cookies used to store session ids. Suppose the
    following page is only accesible to authenticated users:
    另一些例子是cookies用来保存session id的。假设下面这页只能被认证的用户访问：

    http://www.example.com/members/offers.html

    大量的网站使用cookie保存session id，添加一个随机组件给HTTP请求，因此这些在计算指纹
    的时候应该被忽略
    Lot of sites use a cookie to store the session id, which adds a random
    component to the HTTP Request and thus should be ignored when calculating
    the fingerprint.

    由于这个原因，当计算指纹的时候，请求头默认被忽略。如果你想包含指定头，使用include_headers
    参数
    For this reason, request headers are ignored by default when calculating
    the fingeprint. If you want to include specific headers use the
    include_headers argument, which is a list of Request headers to include.

    """
    if include_headers:
        include_headers = tuple(to_bytes(h.lower())
                                 for h in sorted(include_headers))
    cache = _fingerprint_cache.setdefault(request, {})
    if include_headers not in cache:
        fp = hashlib.sha1()
        fp.update(to_bytes(request.method))
        fp.update(to_bytes(canonicalize_url(request.url)))
        fp.update(request.body or b'')
        if include_headers:
            for hdr in include_headers:
                if hdr in request.headers:
                    fp.update(hdr)
                    for v in request.headers.getlist(hdr):
                        fp.update(v)
        cache[include_headers] = fp.hexdigest()
    return cache[include_headers]


def request_authenticate(request, username, password):
    """Autenticate the given request (in place) using the HTTP basic access
    authentication mechanism (RFC 2617) and the given username and password
    """
    request.headers['Authorization'] = basic_auth_header(username, password)


def request_httprepr(request):
    """Return the raw HTTP representation (as bytes) of the given request.
    This is provided only for reference since it's not the actual stream of
    bytes that will be send when performing the request (that's controlled
    by Twisted).
    """
    parsed = urlparse_cached(request)
    path = urlunparse(('', '', parsed.path or '/', parsed.params, parsed.query, ''))
    s = to_bytes(request.method) + b" " + to_bytes(path) + b" HTTP/1.1\r\n"
    s += b"Host: " + to_bytes(parsed.hostname or b'') + b"\r\n"
    if request.headers:
        s += request.headers.to_string() + b"\r\n"
    s += b"\r\n"
    s += request.body
    return s


def referer_str(request):
    """ Return Referer HTTP header suitable for logging. """
    referrer = request.headers.get('Referer')
    if referrer is None:
        return referrer
    return to_native_str(referrer, errors='replace')
