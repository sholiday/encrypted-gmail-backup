#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='EncryptedGmailBackup',
    version = '0.0.4',
    description = 'Backup your GMail account with GPG encryption.',
    author = 'Stephen Holiday',
    author_email = 'stephen.holiday@gmail.com',
    url=  'https://github.com/sholiday/encrypted-gmail-backup',
    py_modules = ['gmailbackup'],
    scripts = ['dobackup.py'],
    entry_points = {
        'console_scripts': [
            'gmail-backup = dobackup:main',
        ]
    },
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python',
    ],
    install_requires=['gnupg', 'psutil'],
    long_description="""
# Encrypted Gmail Backup

Place your config in in `~/.encrypted_gmail_backup`

Sample Config:

    [gmail]
    username = stephen.holiday@gmail.com
    password = changeme

    [gpg]
    keyid = 76AA7B2CF3FD360E
    binary = gpg

    [backup]
    path = /backup/gmail/
    metafile = gmailmeta.txt
    archive = messages.tar

    [gmail]
    username = NONE
    password = NONE
    server   = imap.gmail.com
    folder   = [Gmail]/All Mail

    [gpg]
    # The recipient to encrypt to.
    keyid    = 76AA7B2CF3FD360E
    binary   = gpg
    home     = ~/.gnupg
    encoding = utf-8

    [backup]
    # Target directory for the backup. Must exist and end in a trailing slash.
    path = /tmp/

    # Name of the target archive.
    # Appended to the backup path.
    archive = messages.tar

    # Stores the ID of the last fetched message.
    metafile = gmailmeta.txt

    # If your backup directory is on mounted device,
    # the script can check if the target directory exists first and fail gracefully.
    onexternal = no

    # Ensure only one instance of the script per username.
    use_pid    = yes
    pid_prefix = /tmp/encrypted_gmail_backup

Be sure to `chmod 600 ~/.encrypted_gmail_backup` so that other users can't read your password.

I have MacGPG installed on my system, so I changed binary to:

    binary = /usr/local/MacGPG2/bin/gpg2

Then run `gmail-backup` and it will start to fetch your mail!

Based on Andrew Jennings' [gmail-backup](https://github.com/abjennings/gmail-backup)
    """,
    requires=['gnupg', 'psutil']
)
