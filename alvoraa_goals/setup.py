from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="alvoraa_goals",
    version="0.0.1",
    description="Grace Group Cascaded Goal Management",
    author="Grace Group",
    author_email="hr@gracedrinks.in",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
