from distutils.core import setup

setup(
    name='noticer',
    version='0.1',
    description='Command runner/killer based on filesystem events',
    license='MIT License',
    url='https://github.com/dsalisbury/noticer',
    author='David Salisbury',
    author_email='git@dsho.me',
    py_modules=['noticer'],
    install_requires=[
        'pyinotify',
    ],
    entry_points={
        'console_scripts': [
            'noticer = noticer:_main',
        ],
    },
)
