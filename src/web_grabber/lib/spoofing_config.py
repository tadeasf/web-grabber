"""
Configuration settings for browser fingerprint spoofing.
"""

# Common fonts that appear legitimate
COMMON_FONTS = [
    "Arial",
    "Helvetica",
    "Times New Roman",
    "Calibri",
    "Verdana",
    "Georgia",
]

# Browser window configurations
WINDOW_CONFIGS = {
    "common_resolutions": [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
    ]
}

# WebGL configurations that match real devices
WEBGL_CONFIGS = [
    ("ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)", "Google Inc."),
    ("ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)", "Google Inc."),
    ("ANGLE (AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)", "Google Inc."),
]

# Default configuration that can be imported and used
DEFAULT_CONFIG = {
    "fonts": COMMON_FONTS,
    "humanize": True,
    "block_webrtc": True,
    "disable_coop": False,
    "geoip": True,
    "os": ["windows", "macos"],
    "locale": ["en-US", "en-GB"],  # Common English locales
} 