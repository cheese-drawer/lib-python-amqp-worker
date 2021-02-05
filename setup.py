import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="amqp_worker",
    version="0.1.0",
    author="Andrew Chang-DeWitt",
    author_email="andrew@andrew-chang-dewitt.dev",
    description="Library for creating & managing simple AMQP workers using any of a few different patterns.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cheese-drawer/lib-python-amqp-worker/",
    packages=setuptools.find_packages(),
    install_requires=[
        'aio-pika>=6.7.1,<7.0.0',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)
