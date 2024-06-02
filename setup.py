from setuptools import setup, find_packages

setup(
    name='real_time_translator',
    version='0.1.1',
    description='A real-time audio translator using Azure Cognitive Services and PyQt5',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/jpshag/real-time-translator',
    author='Your Name',
    author_email='jpshag@proton.me',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'PyQt5',
        'pyaudio',
        'numpy',
        'scipy',
        'azure-cognitiveservices-speech',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'real-time-translator=real_time_translator.main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['config.json'],
    },
)
