from setuptools import setup


setup(
    name="janarun",
    version="0.1.0",
    description="A terminal utility.",
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
