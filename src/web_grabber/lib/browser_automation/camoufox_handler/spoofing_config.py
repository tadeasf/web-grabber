"""Configuration settings for browser fingerprint spoofing with Camoufox."""

# Common fonts that appear legitimate
COMMON_FONTS = [
    "Arial",
    "Helvetica",
    "Times New Roman",
    "Calibri",
    "Verdana",
    "Georgia",
    "Tahoma",
    "Trebuchet MS",
    "Segoe UI",
    "Roboto",
    "Open Sans",
]

# Browser window configurations
WINDOW_CONFIGS = {
    "common_resolutions": [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1280, 720),
        (1600, 900),
        (1680, 1050),
        (2560, 1440),
    ],
    "desktop_user_agents": [
        # Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 Edg/94.0.992.47",
    ],
    "mobile_user_agents": [
        # iOS Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        # Android Chrome
        "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Mobile Safari/537.36",
        # Android Firefox
        "Mozilla/5.0 (Android 12; Mobile; rv:93.0) Gecko/93.0 Firefox/93.0",
    ],
}

# WebGL vendor and renderer settings to simulate different GPUs
WEBGL_VENDORS = [
    "Google Inc. (Intel)",
    "Google Inc. (NVIDIA)",
    "Google Inc. (AMD)",
    "Apple Computer, Inc.",
    "WebKit",
]

WEBGL_RENDERERS = [
    "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
    "Apple GPU",
    "Intel Iris OpenGL Engine",
]

# Common plugins to simulate
COMMON_PLUGINS = [
    "Chrome PDF Plugin",
    "Chrome PDF Viewer",
    "Native Client",
]

# Platform settings
PLATFORMS = [
    "Win32",
    "MacIntel",
    "Linux x86_64",
]
