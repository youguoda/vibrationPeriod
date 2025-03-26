from setuptools import setup, find_packages

setup(
    name="vibration_monitor",
    version="1.0.0",
    author="INNOTIME——YOU",
    description="振动监测系统",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "numpy",
        "PyQt5",
        "PyQt5_sip",
        "pyqtgraph",
        "pyserial",
        "scipy",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "vibration-monitor=vibration_monitor.main:main",
        ],
    },
)