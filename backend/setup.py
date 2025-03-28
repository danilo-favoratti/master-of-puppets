from setuptools import setup, find_packages

setup(
    name="master-of-puppets-backend",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "websockets",
        "openai",
        "deepgram-sdk",
        "colorama"
    ]
) 