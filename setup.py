from pathlib import Path

from setuptools import setup


long_description = Path("README.md").read_text(encoding="utf-8")


setup(
    name="janarun",
    version="0.1.0",
    description="A terminal utility.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JanarDot/about-me",
    author="Jana",
    author_email="hello@clandestinalabs.com",
    packages=["aboutme"],
    package_data={"aboutme": ["finger_map.txt", "finger_art.txt"]},
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "janarun=aboutme.main:run",
        ]
    },
)
