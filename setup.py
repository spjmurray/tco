import setuptools

setuptools.setup(
    name='tco',
    version='1.0.4',
    packages=setuptools.find_packages(),
    entry_points = {
        'console_scripts': [
            'tco = tco.main:main'
        ],
    },
)
