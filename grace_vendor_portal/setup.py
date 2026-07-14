from setuptools import setup, find_packages

setup(
    name="grace_vendor_portal",
    version="0.0.1",
    description="Grace Group Vendor Portal with Order & Delivery Tracking",
    author="Grace Group",
    author_email="ops@gracedrinks.in",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
