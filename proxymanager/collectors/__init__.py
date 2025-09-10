from .base import BaseCollector
from .free_proxy_list import FreeProxyListCollector
from .text_file_collector import TextFileCollector

# Dictionary of text-based proxy sources
TEXT_SOURCES = {
    "http": [
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http"
    ],
    "socks4": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5"
    ]
}


# This list is now for collectors that don't need special arguments
# We will handle the TextFileCollector dynamically in main.py
ALL_COLLECTORS_STATIC = [
    FreeProxyListCollector,
]

# Expose everything needed for main.py
__all__ = [
    "BaseCollector",
    "FreeProxyListCollector",
    "TextFileCollector",
    "TEXT_SOURCES",
    "ALL_COLLECTORS_STATIC"
]

