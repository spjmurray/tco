import setuptools

setuptools.setup(
    name='tco',
    version='2.0.0',
    packages=setuptools.find_packages(),
    entry_points = {
        'console_scripts': [
            'tco = tco.main:main'
        ],
    },
)
