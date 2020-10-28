from setuptools import setup, find_packages

setup(
    name='snapshot',
    version='0.1',
    packages=[''],
    url="https://github.com/jamescassidy/automating-aws-with-python/tree/master/ec2-do",
    install_requires=[
        'click',
        'boto3'
    ],
    entry_points='''
        [console_scripts]
        snapshot=snapshot:cli
    ''',
)