from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="alvoraa_goals",
    version="0.0.1",
    description="Alvoraa Cascaded Goal Management",
    author="Alvoraa",
    author_email="support@alvoraa.co",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
