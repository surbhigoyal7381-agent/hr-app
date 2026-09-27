from setuptools import setup, find_packages

setup(
    name="alvoraa_portal",
    version="0.0.1",
    description="Alvoraa Vendor Portal with Order & Delivery Tracking",
    author="Alvoraa",
    author_email="support@alvoraa.co",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe", "anthropic>=1.8,<2"],
)
